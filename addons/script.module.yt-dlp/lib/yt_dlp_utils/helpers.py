from datetime import datetime
import typing as t

from .enums import Quality


__all__ = (
    'extract_metadata',
    'get_formats',
)


def extract_metadata(info: t.Dict[str, t.Any]) -> t.Dict[str, str]:
    """Extracts metadata from the information dictionary of the URL for use with FFmpeg."""
    metadata = {}

    if info.get('title'):
        metadata['title'] = info['title']

    if info.get('description'):
        metadata['description'] = info['description']

    if info.get('timestamp'):
        metadata['date'] = datetime.fromtimestamp(info['timestamp']).isoformat()

    if info.get('playlist'):
        metadata['album'] = info['playlist']

    return metadata


def get_formats(
    skip_hls: bool = False,
    skip_dash: bool = False,
) -> t.Sequence[t.Tuple[Quality, str]]:
    """Returns a list of format argument values for yt-dlp, sorted from best to worst quality."""
    quality_map = {
        Quality.SD_144: 'bestvideo[height<=144]+bestaudio[abr<=128]/best[height<=144]',
        Quality.SD_240: 'bestvideo[height<=240]+bestaudio[abr<=128]/best[height<=240]',
        Quality.SD_360: 'bestvideo[height<=360]+bestaudio[abr<=128]/best[height<=360]',
        Quality.SD_480: 'bestvideo[height<=480]+bestaudio[abr<=128]/best[height<=480]',
        Quality.HD_720: 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        Quality.FHD_1080: 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        Quality.QHD_1440: 'bestvideo[height<=1440]+bestaudio/best[height<=1440]',
        Quality.UHD_2160: 'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
        Quality.BEST: 'bestvideo+bestaudio/best',
        Quality.AUDIO_ONLY: 'bestaudio/best',
        Quality.VIDEO_ONLY: 'bestvideo/best',
    }

    if not skip_hls:
        quality_map[Quality.HLS] = 'bestaudio/best'

    if not skip_dash:
        quality_map[Quality.DASH] = 'bestaudio/best'

    return [
        (q, quality_map[q])
        for q in sorted(Quality, key=lambda v: v.value)
    ]
