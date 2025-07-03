import datetime
import enum
import re
import time
import typing as t

import yt_dlp
import xbmc


class safe_datetime(datetime.datetime):
    @classmethod
    def strptime(cls, date_string, fmt):
        return datetime.datetime(*(time.strptime(date_string, fmt)[:6]))


datetime.datetime = safe_datetime


class Quality(enum.IntEnum):
    SD_144 = 144
    SD_320 = 320
    SD_480 = 480
    SD_540 = 540
    HD = 720
    FHD = 1080
    QHD = 1440
    UHD = 2160
    BEST = -1


class VideoInfo(t.NamedTuple):
    play_url: str
    quality: Quality
    info: t.Dict[str, t.Any]

    @property
    def duration(self) -> int:
        return self.info.get('duration', -1)

    @property
    def title(self) -> str:
        return self.info.get('title', '')


def _get_screen_resolution() -> t.Tuple[int, int]:
    """Returns the screen resolution set in the settings."""
    resolution = xbmc.getInfoLabel('System.ScreenResolution')
    found = re.findall(r'\d+', resolution)
    width, height = (int(i) for i in found[:2])
    return width, height


def _get_video_info(page_url: str):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(page_url, download=False)


def extract_source(url, quality: t.Optional[Quality] = None) -> VideoInfo:
    screen_width, screen_height = _get_screen_resolution()

    if quality is None:
        quality = max(Quality, key=lambda q: (screen_width <= q.value * 16 // 9) or screen_height <= q.value)

    width = quality.value * 16 // 9
    height = quality.value

    info = _get_video_info(url)
    fmt = max(
        filter(
            lambda f: (
                ('vcodec' in f and f['vcodec'] != 'none') and
                ('acodec' in f and f['acodec'] != 'none') and
                ('width' in f and f['width'] <= width) and
                ('height' in f and f['height'] <= height)
            ),
            info['formats']
        ),
        key=lambda f: (f['height'], f.get('fps', 0), f.get('tbr', 0))
    )

    return VideoInfo(play_url=fmt['url'], quality=quality, info=info)


if __name__ == '__main__':
    _get_screen_resolution = lambda: (1280, 720)

    url = 'https://rutube.ru/video/b4f925173ff424a12e32f8e04464396d/'
    # url = 'https://www.youtube.com/watch?v=VKiB93koF40'
    info = extract_source(url)
    print(info.title, info.quality, info.play_url)
