from datetime import datetime
import enum
import logging
import pathlib
import tempfile
import typing as t

from kodi_useful import alert, prompt
from kodi_useful.utils import get_addon
import pyxbmct
import vk_api
import xbmcgui
from xbmcvfs import translatePath


PHOTO_SIZE_MAP = {
    's': 75,
    'm': 130,
    'x': 604,
    'o': 130,
    'p': 200,
    'q': 320,
    'r': 510,
    'y': 807,
    'z': 1080,
    'w': 2560,
}

logger = logging.getLogger()


class AgeLimit(enum.IntEnum):
    """Возрастное ограничение."""
    NO = 1
    SIXTEEN = 2
    EIGHTEEN = 3


class ErrorCode(enum.IntEnum):
    """Коды ошибок VK API."""
    AUTHORIZATION_FAILED = 5


class CaptchaDialog(pyxbmct.AddonDialogWindow):
    """VK Captcha window"""

    def __init__(self, captcha_url: str, captcha_file: str = '', title='') -> None:
        super().__init__(title)

        self.captcha_url = captcha_url
        self.captcha_file = captcha_file
        self.canceled = False

        width = xbmcgui.getScreenWidth() * 70 // 100
        height = xbmcgui.getScreenHeight() * 73 // 100

        self.setGeometry(width, height, 8, 3)
        self.setup_controls()
        self.setup_navigation()

    def exec_(self) -> t.Tuple[bool, str]:
        self.doModal()
        return self.canceled, self.get_value()

    def get_value(self) -> str:
        return self.value_field.getText()

    def handle_click_ok(self):
        if not self.get_value():
            xbmcgui.Dialog().ok('Error', 'Value required')
        else:
            self.close()

    def onAction(self, action):
        self.canceled = action == xbmcgui.ACTION_PREVIOUS_MENU
        super().onAction(action)

    @classmethod
    def open(
        cls,
        captcha_url: str,
        captcha_file: str = '',
        title='Enter captcha value'
    ) -> t.Tuple[bool, str]:
        window = cls(captcha_url=captcha_url, captcha_file=captcha_file, title=title)
        canceled, value = window.exec_()
        del window
        return canceled, value

    def setup_controls(self) -> None:
        """Set up UI controls"""
        image = pyxbmct.Image(self.captcha_file or self.captcha_url)
        self.placeControl(image, 0, 0, rowspan=6, columnspan=3)

        url_label = pyxbmct.Label(
            self.captcha_url,
            alignment=pyxbmct.ALIGN_CENTER_Y,
        )
        self.placeControl(url_label, 6, 0, columnspan=3)

        self.value_field = pyxbmct.Edit(
            '',
            _alignment=pyxbmct.ALIGN_CENTER_Y,
        )
        self.placeControl(self.value_field, 7, 0, columnspan=2)

        self.ok_btn = pyxbmct.Button('OK')
        self.connect(self.ok_btn, self.handle_click_ok)
        self.placeControl(self.ok_btn, 7, 2)

    def setup_navigation(self):
        """Set up keyboard/remote navigation between controls."""
        self.value_field.controlRight(self.ok_btn)
        self.ok_btn.controlLeft(self.value_field)
        self.setFocus(self.value_field)


def auth_handler() -> t.Tuple[int, bool]:
    code = prompt('Enter authentication code', required=True, type_cast=int)

    if code:
        remember_device = True
        return code.value, remember_device

    raise vk_api.AuthError(
        'You have cancelled the authentication code entry.'
    )


def captcha_handler(captcha: vk_api.Captcha):
    logger.debug('VK auth need captcha: %s' % captcha.get_url())

    with tempfile.NamedTemporaryFile() as f:
        f.write(captcha.get_image())
        f.flush()

        canceled, value = CaptchaDialog.open(
            captcha_url=captcha.get_url(),
            captcha_file=f.name,
        )

        if canceled:
            raise vk_api.AuthError('Recaptcha required.')

        return captcha.try_again(value)


def get_original_photo(photo):
    size_order = sorted(PHOTO_SIZE_MAP.keys())
    largest_url = None
    largest_size_type = size_order[0]

    for size in photo['sizes']:
        if size_order.index(size['type']) > size_order.index(largest_size_type):
            largest_size_type = size['type']
            largest_url = size['url']

    return {
        'type': 'base',
        'height': photo.get('height', 0),
        'url': largest_url,
        'width': photo.get('weight', 0),
    }


def get_vk_session() -> vk_api.VkApi:
    last_login = get_addon().getSettingString('vk_last_login') or None
    logger.debug(f'Last login => {last_login}')

    profile_path = pathlib.Path(
        translatePath(get_addon().getAddonInfo('profile'))
    )
    profile_path.mkdir(parents=True, exist_ok=True)
    config_filename = profile_path / 'vk_config.json'

    return vk_api.VkApi(
        last_login,
        config_filename=config_filename,
        auth_handler=auth_handler,
        captcha_handler=captcha_handler,
    )


vk_session = get_vk_session()
vk = vk_session.get_api()
tools = vk_api.VkTools(vk_session)


def login():
    username = prompt('Login', required=True, default=vk_session.login)
    password = prompt('Password', required=True, hidden=True) if username else None

    if not username or not password:
        alert(
            'Credentials required',
            'To use the application, you need to provide a login and password.'
        )
        return False

    vk_session.login = username.value
    vk_session.password = password.value

    try:
        vk_session.auth(reauth=True, token_only=True)
        get_addon().setSettingString('vk_last_login', username.value)
        return True
    except vk_api.AuthError as err:
        alert('Authentication error', str(err))
        return False


def logout():
    vk_session.storage.clear_section()
    vk_session.storage.save()


def get_friends(
    limit: int = 50,
    offset: int = 0,
    skip_deactivated: bool = False,
):
    r = vk.friends.get(
        count=limit,
        offset=offset,
        fields=['photo_200_orig', 'about'],
    )

    if skip_deactivated:
        r['items'] = [i for i in r['items'] if 'deactivated' not in i]

    for friend in r['items']:
        friend.setdefault('about', '')
        friend['fullname'] = '{f[first_name]} {f[last_name]}'.format(f=friend)

    return r


def get_groups(
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    skip_deactivated: bool = False,
    age_limit: int = AgeLimit.NO,
):
    r = vk.groups.get(
        user_id=user_id,
        extended=1,
        fields=('age_limits', 'description'),
        count=limit,
        offset=offset,
    )

    groups = filter(lambda i: i['age_limits'] <= age_limit, r['items'])
    r['items'] = []

    if skip_deactivated:
        groups = filter(lambda i: 'deactivated' not in i, groups)

    for group in groups:
        group['oid'] = '-%d' % group['id']
        r['items'].append(group)

    return r


def get_photo_albums(
    owner_id: int,
    limit: int = 50,
    offset: int = 0,
):
    r = vk.photos.getAlbums(
        owner_id=owner_id,
        need_system=1,
        need_covers=1,
        count=limit,
        offset=offset,
    )

    for album in r['items']:
        album.setdefault('description', '')

    return r


def get_video_albums(
    owner_id: int,
    limit: int = 50,
    offset: int = 0,
):
    r = vk.video.getAlbums(
        owner_id=owner_id,
        count=limit,
        offset=offset,
        need_system=1,
        extended=1,
    )

    for album in r['items']:
        album['updated_time'] = datetime.fromtimestamp(album['updated_time'])
        album.setdefault('photo_160', None)
        album.setdefault('photo_320', None)

    return r


def get_photos(
    owner_id: int,
    album_id: int,
    limit: int = 50,
    offset: int = 0,
):
    r = vk.photos.get(
        owner_id=owner_id,
        album_id=album_id,
        rev=1,
        photo_sizes=1,
        count=limit,
        offset=offset,
    )

    for photo in r['items']:
        photo['date'] = datetime.fromtimestamp(photo['date'])

        if 'orig_photo' not in photo:
            photo['orig_photo'] = get_original_photo(photo)

        photo.update({
            'photo_%d' % PHOTO_SIZE_MAP[s['type']]: s['url']
            for s in photo['sizes']
        })

    return r


def get_videos(
    owner_id: int,
    album_id: int,
    limit: int = 50,
    offset: int = 0,
):
    r = vk.video.get(
        owner_id=owner_id,
        album_id=album_id,
        count=limit,
        offset=offset,
    )
    r['items'] = [v for v in r['items'] if 'player' in v]

    for video in r['items']:
        video.setdefault('platform', 'VK')

    return r
