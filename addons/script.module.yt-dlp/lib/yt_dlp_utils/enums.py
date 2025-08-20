import enum


class Quality(enum.Enum):
    """Universal video quality presets for yt-dlp."""

    # --- Универсальный выбор ---
    BEST = 1

    # --- Высокие разрешения (полное аудио) ---
    UHD_2160 = 10
    QHD_1440 = 11
    FHD_1080 = 12
    HD_720 = 13

    # --- Низкие разрешения (LITE: ограничение аудио по битрейту) ---
    SD_480 = 20
    SD_360 = 21
    SD_240 = 22
    SD_144 = 23

    # --- Специальные случаи ---
    VIDEO_ONLY = 30
    AUDIO_ONLY = 31
    HLS = 2
    DASH = 3
