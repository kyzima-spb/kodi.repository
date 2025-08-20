from functools import partial
import glob
import os
import pathlib
import re
import tempfile
import typing as t
import uuid

from kodi_useful import Addon
from kodi_useful import fs
import xbmcgui
import yt_dlp

from .enums import Quality
from .ffmpeg_metadata import read_metadata, write_metadata
from .helpers import extract_metadata, get_formats


class DownloaderError(Exception):
    pass


class DownloadCanceled(DownloaderError):
    def __init__(self, filename: str) -> None:
        self.filename = filename


class YTDownloader:
    def __init__(self, download_dir: str) -> None:
        self.addon = Addon.get_instance('script.module.yt-dlp')
        self.download_dir = download_dir

    def _clear_temp_files(self, output_file: str) -> None:
        pathlib.Path(output_file).unlink(missing_ok=True)

        for path in (pathlib.Path(i) for i in glob.iglob(f'{output_file}.*')):
            if path.suffix in {'.part', '.ytdl', '.frag', '.temp', '.tmp', '.jpg', '.png', '.json'}:
                path.unlink(missing_ok=True)

    def _format_size(self, size: int, units: t.Tuple[str, ...]) -> str:
        idx = 0

        while size >= 1024 and idx < len(units) - 1:
            size /= 1024
            idx += 1

        return f'{size:.2f} {units[idx]}'

    def _download_progress_hook(self, d, *, progress_dialog):
        if progress_dialog.iscanceled():
            raise DownloadCanceled(d.get('filename'))

        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes') or 0
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            speed = d.get('speed') or 0
            eta = int(d.get('eta') or 0)

            percent = int(downloaded * 100 / total) if total > 0 else 0

            downloaded_str = self._format_size(downloaded, units=('B', 'Kb', 'Mb', 'Gb', 'Tb'))
            speed_str = self._format_size(speed, units=('B/s', 'KB/s', 'MB/s', 'GB/s'))

            progress_dialog.update(
                percent,
                '\n'.join((
                    self._localize('Downloaded: %(total)s', total=downloaded_str),
                    self._localize('Download speed: %(speed)s', speed=speed_str),
                    f'ETA: {eta} sec.',
                ))
            )
        elif d['status'] == 'finished':
            progress_dialog.update(100, '')

    def _localize(self, message: str, *args: t.Any, **kwargs: t.Any) -> str:
        return self.addon.localize(message, *args, **kwargs)

    def _write_metadata_progress_hook(self, ffmpeg, d, progress_dialog, filename, duration):
        if progress_dialog.iscanceled():
            ffmpeg.stop()
            raise DownloadCanceled(filename)

        if d['progress'] == 'continue':
            out_time = re.sub(r'\.\d*$', '', d.get('out_time', 'n/a'))

            percent = (int(d.get('out_time_ms'), 0) * 100 // duration) if duration else 0

            progress_dialog.update(
                percent,
                '\n'.join((
                    self._localize('Processed: %(value)s', value=out_time),
                    self._localize('Bitrate: %(value)s', value=d['bitrate']),
                    f"FPS: {d['fps']}",
                ))
            )
        elif d['progress'] == 'end':
            progress_dialog.update(100, '')

    def notification(self, message: str, icon: str = xbmcgui.NOTIFICATION_INFO) -> None:
        xbmcgui.Dialog().notification(self._localize('Download status'), message, icon)

    def start(
        self,
        url: str,
        output_file: str,
        quality: t.Optional[Quality] = None,
        metadata: t.Optional[t.Dict[str, str]] = None,
        thumbnail: t.Optional[str] = None,
        headers: t.Optional[t.Dict[str, str]] = None,
    ) -> None:
        progress_dialog = xbmcgui.DialogProgress()
        ydl_opts = {
            'quiet': True,
            'noprogress': True,
            'progress_hooks': [
                partial(self._download_progress_hook, progress_dialog=progress_dialog),
            ],
            'http_headers': headers or {},
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            target_file = yt_dlp.utils.sanitize_path(
                os.path.join(
                    self.download_dir, ydl.evaluate_outtmpl(output_file, info, sanitize=False)
                )
            )

        if fs.exists(target_file) and not xbmcgui.Dialog().yesno(
            self._localize('The file exists'),
            self._localize('Retry downloading the file?\nThe existing file will be overwritten.')
        ):
            return None

        video_formats = get_formats()

        if quality is None:
            quality_idx = xbmcgui.Dialog().select(
                self._localize('Select quality'),
                [self._localize(str(q)) for q, _ in video_formats],
            )

            if quality_idx < 0:
                return None

            quality, format_string = video_formats[quality_idx]
        else:
            format_string = dict(video_formats)[quality]

        target_dir = os.path.dirname(target_file)
        fs.makedirs(target_dir)

        metadata = {
            **extract_metadata(info),
            **(metadata or {}),
        }

        if thumbnail is None and 'thumbnail' in info:
            thumbnail = info['thumbnail']

        with tempfile.TemporaryDirectory() as d:
            temp_link = os.path.join(d, str(uuid.uuid4()))
            fs.symlink(target_dir, temp_link)

            self.addon.logger.debug(format_string)

            ydl_opts['outtmpl'] = os.path.join(temp_link, f'{uuid.uuid4()}.%(ext)s')
            ydl_opts['format'] = format_string

            try:
                progress_dialog.create(
                    self._localize('Downloading'),
                    self._localize('Preparing to download file...'),
                )
                progress_dialog.update(0, '')

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    temp_file = ydl.prepare_filename(info)

                progress_dialog.create(
                    self._localize('Adding Metadata'),
                    self._localize('Wait...')
                )
                progress_dialog.update(0, '')

                duration = info.get(
                    'duration',
                    read_metadata(temp_file).get('format', {}).get('duration')
                )
                duration_ms = None if duration is None else int(float(duration) * 1_000_000)

                write_metadata(
                    temp_file,
                    metadata=metadata,
                    thumbnail=thumbnail,
                    progress_hook=partial(
                        self._write_metadata_progress_hook,
                        progress_dialog=progress_dialog,
                        filename=temp_file,
                        duration=duration_ms,
                    ),
                )

                fs.rename(temp_file, target_file)

                self.notification(self._localize('File saved as %(filename)s', filename=target_file))
            except DownloadCanceled as err:
                self._clear_temp_files(err.filename)
                self.notification(self._localize('Canceled by user'))
            except Exception as err:
                self.addon.logger.error(str(err))
                raise
            #     self.notification(str(err), xbmcgui.NOTIFICATION_ERROR)
            finally:
                progress_dialog.close()
