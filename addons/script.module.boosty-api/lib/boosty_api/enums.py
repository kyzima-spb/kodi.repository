import enum


class MediaType(str, enum.Enum):
    """Type of returned contents from the media section."""
    ALL = 'all'
    AUDIO = 'audio'
    IMAGE = 'image'
    VIDEO = 'video'
    UNKNOWN = 'unknown'


MEDIA_TYPE_MAP = {
    'ok_video': MediaType.VIDEO,
    'image': MediaType.IMAGE,
    'audio_file': MediaType.AUDIO,
}


class Quality(str, enum.Enum):
    """Video quality."""
    SD_144 = 'tiny'
    SD_240 = 'lowest'
    SD_360 = 'low'
    SD_480 = 'medium'
    HD = 'high'
    FHD = 'full_hd'
    QHD = 'quad_hd'
    UHD = 'ultra_hd'
    HLS = 'hls'
    DASH = 'dash'
