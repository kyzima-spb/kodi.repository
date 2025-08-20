import itertools
import json
import os
import pathlib
import subprocess
import tempfile
import typing as t


try:
    from kodi_useful import Addon
    logger = Addon.get_instance('script.module.yt-dlp').logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())


__all__ = (
    'convert_thumbnail',
    'read_metadata',
    'write_metadata',
    'FFMpeg',
    'FFMpegError',
)


class FFMpegError(Exception):
    pass


class FFMpeg:
    def __init__(
        self,
        progress_hook: t.Optional[t.Callable[['FFMpeg', t.Dict[str, str]], None]] = None,
    ) -> None:
        self._process = None
        self._stopped = True
        self._progress_hook = progress_hook

    def _read_stdout(self) -> None:
        data = {}

        for line in map(str.strip, filter(lambda i: '=' in i, self._process.stdout)):
            if self._stopped:
                break

            name, value = line.strip().split('=', 1)
            data[name] = value

            if name == 'progress':
                if callable(self._progress_hook):
                    self._progress_hook(self, data)

                data = {}

                if value == 'end':
                    break

    def __call__(self, args):
        self._process = subprocess.Popen(
            [
                str(i).encode('utf-8')
                for i in ('ffmpeg', '-v', 'error', '-progress', '-', *args)
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._stopped = False

        try:
            self._read_stdout()

            return_code = self._process.wait()

            if return_code != 0:
                raise FFMpegError(self._process.stderr.read())
        finally:
            self._process = None
            self._stopped = True

    def stop(self):
        self._stopped = True

        if self._process is not None and self._process.poll() is None:
            self._process.terminate()


def read_metadata(filename: t.Union[str, pathlib.Path]) -> t.Dict[str, t.Any]:
    """Returns data about a media file from the ffprobe utility."""
    try:
        output = subprocess.check_output(
            ['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', filename],
            stderr=subprocess.PIPE,
        )
        data = json.loads(output)
        return data
    except subprocess.CalledProcessError as err:
        logger.error(f'ffprobe error: {err.stderr.strip()}')
    except json.JSONDecodeError as err:
        logger.error(f'JSON error: {err}')
    return {}


def convert_thumbnail(source: str) -> t.Optional[str]:
    """Converts an image to JPEG and returns the path to the temporary file."""
    fd, path = tempfile.mkstemp(suffix='.jpg')
    os.close(fd)

    try:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', source, path], stderr=subprocess.PIPE)
        return path
    except subprocess.CalledProcessError as err:
        logger.error(f'Convert thumbnail error: {err.stderr.strip()}')
        os.remove(path)
        return None


def write_metadata(
    filename: str,
    metadata: t.Optional[t.Dict[str, str]] = None,
    thumbnail: t.Optional[str] = None,
    progress_hook: t.Optional[t.Callable[['FFMpeg', t.Dict[str, str]], None]] = None,
) -> None:
    input_file = pathlib.Path(filename).absolute()
    output_file = input_file.with_suffix('.output' + input_file.suffix)
    thumbnail = convert_thumbnail(thumbnail) if thumbnail else None

    input_files = [('-i', str(input_file))]
    temp_files = [output_file]
    map_args = []
    ffmpeg_args = [('-y',), ('-codec', 'copy')]

    if thumbnail:
        idx = len(input_files)
        map_args.append(('-map', f'{idx}'))
        ffmpeg_args.append((f'-disposition:v:{idx}', 'attached_pic'))

        input_files.append(('-i', thumbnail))
        temp_files.append(pathlib.Path(thumbnail))

    if not metadata and not thumbnail:
        return None

    map_args[:0] = [
        ('-map', f"0:{stream['index']}")
        for stream in read_metadata(input_file).get('streams', [])
        if stream['codec_type'] != 'video' or stream.get('disposition', {}).get('attached_pic') != 1 or not thumbnail
    ]

    if metadata:
        ffmpeg_args.extend(('-metadata', f'{k}={v}') for k, v in metadata.items())

    try:
        ffmpeg = FFMpeg(progress_hook=progress_hook)
        ffmpeg([
            *itertools.chain(*input_files, *map_args, *ffmpeg_args),
            str(output_file),
        ])
        output_file.rename(input_file)
    except FFMpegError as err:
        logger.error(str(err))
        raise
    finally:
        for p in temp_files:
            p.unlink(missing_ok=True)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} PATH', file=sys.stderr)
        sys.exit(1)

    filename = sys.argv[1]
    print(read_metadata(filename))
