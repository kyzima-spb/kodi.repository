from textwrap import dedent
import logging
import sys

import xbmc
from kodi_useful.core import Router
import xbmcgui
import xbmcplugin
from kodi_useful import alert, prompt, ListItem
from kodi_useful.utils import get_addon, init_logger
import vk_api

init_logger()
logger = logging.getLogger()

from . import api


router = Router(sys.argv[0])
HANDLE = int(sys.argv[1])
ADDON = get_addon()
DEBUG = True


def pagination(func):
    def wrapper(q):
        per_page = q.get_int('per_page', ADDON.getSettingInt('items_per_page'))
        offset = q.get_int('offset', 0)
        return func(q=q, per_page=per_page, offset=offset)
    return wrapper


@router.route()
def index(q):
    content_type = q.get_string('content_type')

    menu = [
        ('video.albums', 'Поиск', False, 'video'),
        (list_friends, 'Друзья', True, None),
        (list_photo_albums, 'Фотографии', True, 'image'),
        (list_video_albums, 'Видеозаписи', True, 'video'),
        (list_groups, 'Сообщества', True, None),
    ]

    for name, title, is_folder, ct in menu:
        if ct is None or ct == content_type:
            url = router.url_for(name)
            item = ListItem(title)
            xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=is_folder)

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=DEBUG)


@router.route('friends.get')
@pagination
def list_friends(q, per_page, offset):
    xbmcplugin.setPluginCategory(HANDLE, 'Friends')

    r = api.get_friends(
        limit=per_page,
        offset=offset,
        skip_deactivated=ADDON.getSettingBool('hide_deactivated_friends'),
    )
    route_handler = list_photo_albums if q.get_string('content_type') == 'image' else list_video_albums

    for friend in r['items']:
        url = router.url_for(route_handler, owner_id=friend['id'])
        description = dedent(f'''
        [B]{friend['fullname']}[/B]
        
        {friend['about']}
        ''')
        item = ListItem(friend['fullname'])
        item.setInfo('video', {'plot': description})
        item.setArt({'thumb': friend['photo_200_orig']})
        xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=True)

    offset += per_page

    if r['count'] > offset:
        url = router.url_from_current(offset=offset)
        item = ListItem.next_item(per_page, offset)
        xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=DEBUG)


@router.route('groups.get')
@pagination
def list_groups(q, per_page, offset):
    xbmcplugin.setPluginCategory(HANDLE, 'Groups')
    xbmcplugin.setContent(HANDLE, 'albums')

    r = api.get_groups(
        user_id=q.get_int('user_id'),
        skip_deactivated=ADDON.getSettingBool('hide_deactivated_groups'),
        age_limit=ADDON.getSettingInt('age_limit') + 1,
        limit=per_page,
        offset=offset,
    )
    route_handler = list_photo_albums if q.get_string('content_type') == 'image' else list_video_albums

    for group in r['items']:
        url = router.url_for(route_handler, owner_id=group['oid'])
        item = ListItem(group['name'])
        item.setArt({'thumb': group['photo_200']})
        item.setInfo('video', {
            'plot': group['description'],
        })
        xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=True)

    offset += per_page

    if r['count'] > offset:
        url = router.url_from_current(offset=offset)
        item = ListItem.next_item(per_page, offset)
        xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=DEBUG)


@router.route('photo.albums')
@pagination
def list_photo_albums(q, per_page, offset):
    xbmcplugin.setPluginCategory(HANDLE, 'Albums')
    xbmcplugin.setContent(HANDLE, 'albums')

    r = api.get_photo_albums(
        owner_id=q.get_int('owner_id'),
        limit=per_page,
        offset=offset,
    )

    for album in r['items']:
        url = router.url_for(
            photo_list, id=album['id'], owner_id=album['owner_id'], title=album['title']
        )
        item = ListItem(album['title'])
        item.setInfo('video', {'plot': album['description']})
        item.setArt({'thumb': album['thumb_src']})
        xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=True)

    offset += per_page

    if r['count'] > offset:
        url = router.url_from_current(offset=offset)
        item = ListItem.next_item(per_page, offset)
        xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=DEBUG)


@router.route('photos.list')
@pagination
def photo_list(q, per_page, offset):
    xbmcplugin.setPluginCategory(HANDLE, q.get_string('title'))
    xbmcplugin.setContent(HANDLE, 'images')

    r = api.get_photos(
        owner_id=q.get_int('owner_id'),
        album_id=q.get_int('id'),
        limit=per_page,
        offset=offset,
    )

    for photo in r['items']:
        url = photo['orig_photo']['url']
        uploaded = photo['date'].strftime('%Y-%m-%d %H:%M:%S')

        item = ListItem(uploaded)
        item.setInfo('pictures', {
            'date': uploaded,
            'title': uploaded,
            'picturepath': url,
        })
        # item.setInfo('video', {'plot': photo['text']})
        item.setArt({
            # 'icon': photo.get('photo_320', photo['photo_75'])
        })
        xbmcplugin.addDirectoryItem(HANDLE, url, item)

    offset += per_page

    if r['count'] > offset:
        url = router.url_from_current(offset=offset)
        item = ListItem.next_item(per_page, offset)
        xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=DEBUG)


@router.route('video.albums')
@pagination
def list_video_albums(q, per_page, offset):
    xbmcplugin.setPluginCategory(HANDLE, 'Albums')
    xbmcplugin.setContent(HANDLE, 'albums')

    r = api.get_video_albums(
        owner_id=q.get_int('owner_id'),
        limit=per_page,
        offset=offset,
    )

    for album in r['items']:
        url = router.url_for(
            video_list, id=album['id'], owner_id=album['owner_id'], title=album['title']
        )
        item = ListItem(album['title'])
        item.setInfo('video', {
            'plot': 'Updated: {:%d.%m.%Y %H:%M:%S}'.format(album['updated_time']),
        })
        item.setArt({'thumb': album['photo_320']})
        xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=True)

    offset += per_page

    if r['count'] > offset:
        url = router.url_from_current(offset=offset)
        item = ListItem.next_item(per_page, offset)
        xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=DEBUG)


@router.route('video.list')
@pagination
def video_list(q, per_page, offset):
    xbmcplugin.setPluginCategory(HANDLE, q.get_string('title'))
    xbmcplugin.setContent(HANDLE, 'videos')

    r = api.get_videos(
        owner_id=q.get_int('owner_id'),
        album_id=q.get_int('id'),
        limit=per_page,
        offset=offset,
    )

    for video in r['items']:
        url = router.url_for(play_video, player=video['player'])
        description = dedent(f'''
        [B]{video['platform']}[/B]
        {video['description']}
        ''')
        item = ListItem(video['title'])
        item.setProperty('IsPlayable', 'true')
        item.setInfo('video', {
            'plot': description,
            'duration': video['duration'],
        })
        item.setArt({
            'thumb': video['photo_320'],
        })
        xbmcplugin.addDirectoryItem(HANDLE, url, item)

    offset += per_page

    if r['count'] > offset:
        url = router.url_from_current(offset=offset)
        item = ListItem.next_item(per_page, offset)
        xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=DEBUG)


from YDStreamExtractor import getVideoInfo, setOutputCallback, overrideParam


def extract_source(url, quality=None, **params):
    for key, value in params.items():
        overrideParam(key, value)

    video_info = getVideoInfo(url, quality)

    if video_info:
        if video_info.hasMultipleStreams():
            # More than one stream found, Ask the user to select a stream
            logger.debug(f'hasMultipleStreams: {video_info}')

        if video_info:
            # Content Lookup needs to be disabled for dailymotion videos to work
            # if video_info.sourceName == "dailymotion":
            #     self._extra_commands["setContentLookup"] = False

            return video_info.streamURL()


@router.route('play')
def play_video(q):
    """Воспроизводит видео файл."""
    player = q.get_string('player')
    path = extract_source(player)
    succeeded = path is not None
    logger.debug('Player: {}, Url: {}'.format(player, path))
    item = ListItem(offscreen=True)
    item.setPath(path)
    # Pass the item to the Kodi player
    xbmcplugin.setResolvedUrl(HANDLE, succeeded, item)


from urllib.error import URLError
from urllib.request import urlopen


def has_internet_connection(url: str) -> bool:
    try:
        urlopen(url)
        return True
    except URLError as err:
        logger.debug(f'Check internet connection failed with error - {err}')
        return False


def catch_api_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except vk_api.ApiError as err:
            if err.code == api.ErrorCode.AUTHORIZATION_FAILED:
                return err.try_method() if api.login() else None
            logger.debug(err)
            raise
    return wrapper


@catch_api_error
def main():
    if not has_internet_connection('https://vk.com'):
        alert(
            'Network error',
            'There is no internet connection or the VK server is not available.'
        )

    if api.vk_session.login:
        api.vk_session.auth(token_only=True)

    router.dispatch()
