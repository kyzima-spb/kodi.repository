from functools import partial
import glob
import pathlib
import re
import typing as t

import xbmcgui
from yt_dlp import YoutubeDL
from kodi_useful import current_addon

from .ffmpeg_metadata import read_metadata, write_metadata


class DownloadCanceled(Exception):
    def __init__(self, filename: str) -> None:
        self.filename = filename


class YTDownloader:
    def __init__(self, output_path: str) -> None:
        self.output_path = output_path
        self.progress = xbmcgui.DialogProgress()

    def _format_size(self, size: int, units: tuple[str, ...]) -> str:
        idx = 0

        while size >= 1024 and idx < len(units) - 1:
            size /= 1024
            idx += 1

        return f'{size:.2f} {units[idx]}'

    def _show_status(self, message: str, icon: str = xbmcgui.NOTIFICATION_INFO) -> None:
        xbmcgui.Dialog().notification('Download status', message, icon)

    def _clear_temp_files(self, output_file: str) -> None:
        pathlib.Path(output_file).unlink(missing_ok=True)

        for path in (pathlib.Path(i) for i in glob.iglob(f'{output_file}.*')):
            if path.suffix in {'.part', '.ytdl', '.frag', '.temp', '.tmp'}:
                path.unlink(missing_ok=True)

    def download_progress_hook(self, d):
        if self.progress.iscanceled():
            raise DownloadCanceled(d.get('filename'))

        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes') or 0
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            speed = d.get('speed') or 0
            eta = int(d.get('eta') or 0)

            percent = int(downloaded * 100 / total) if total > 0 else 0

            downloaded_str = self._format_size(downloaded, units=('B', 'Kb', 'Mb', 'Gb', 'Tb'))
            speed_str = self._format_size(speed, units=('B/s', 'KB/s', 'MB/s', 'GB/s'))

            self.progress.update(
                percent,
                '\n'.join((
                    f'Downloaded: {downloaded_str}',
                    f'Download speed: {speed_str}',
                    f'ETA: {eta} sec.',
                ))
            )
        elif d['status'] == 'finished':
            self.progress.update(100, '')

    def metadata_progress_hook(self, ffmpeg, d, filename, duration):
        if self.progress.iscanceled():
            ffmpeg.stop()
            raise DownloadCanceled(filename)

        if d['progress'] == 'continue':
            out_time = re.sub(r'\.\d*$', '', d.get('out_time', 'n/a'))

            percent = (int(d.get('out_time_ms'), 0) * 100 // duration) if duration else 0

            current_addon.logger.debug(d)
            self.progress.update(
                percent,
                '\n'.join((
                    f'Processed: {out_time}',
                    f"Bitrate: {d['bitrate']}",
                    f"FPS: {d['fps']}",
                ))
            )
        elif d['progress'] == 'end':
            self.progress.update(100, '')

    def start(
        self,
        url: str,
        metadata: t.Optional[t.Dict[str, str]] = None,
        thumbnail: t.Optional[str] = None,
        headers: t.Optional[t.Dict[str, str]] = None,
    ) -> None:
        headers = headers or {}

        ydl_opts = {
            'outtmpl': self.output_path,
            'quiet': True,
            'noprogress': True,
            'progress_hooks': [self.download_progress_hook],
            'http_headers': headers,
        }

        try:
            self.progress.create('Downloading', 'Preparing to download file...')

            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            self.progress.create('Adding Metadata', 'Wait...')

            filename = ydl.prepare_filename(info)

            duration = read_metadata(filename).get('format', {}).get('duration')
            duration_ms = None if duration is None else int(float(duration) * 1_000_000)

            write_metadata(
                filename,
                metadata=metadata,
                thumbnail=thumbnail,
                progress_hook=partial(
                    self.metadata_progress_hook,
                    filename=filename,
                    duration=duration_ms,
                ),
            )

            self._show_status(f'File saved as {filename}')
        except DownloadCanceled as err:
            self._clear_temp_files(err.filename)
            self._show_status('Canceled by user')
        except Exception as err:
            current_addon.logger.error(str(err))
            self._show_status(str(err), xbmcgui.NOTIFICATION_ERROR)
        finally:
            self.progress.close()
