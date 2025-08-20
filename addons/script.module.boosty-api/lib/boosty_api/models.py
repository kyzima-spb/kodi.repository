from collections import UserDict
from dataclasses import asdict, dataclass, field, InitVar
from datetime import date, datetime, time
from functools import cached_property
import itertools
import json
import typing as t

from .enums import MediaType, MEDIA_TYPE_MAP
from .utils import extract_content, extract_images, extract_text, to_timestamp


@dataclass
class Collection:
    limit: int
    offset: t.Union[int, str]
    is_last: bool
    iterable: t.Sequence[t.Any]
    extra: t.Dict[str, t.Any] = field(default_factory=dict)

    def __iter__(self):
        return iter(self.iterable)


@dataclass
class MediaCollection(Collection):
    def __iter__(self):
        media_type_map = {
            'ok_video': MediaType.VIDEO,
            'image': MediaType.IMAGE,
            'audio_file': MediaType.AUDIO,
        }

        for media_post in super().__iter__():
            media_type_counters = {
                i: itertools.count()
                for i in itertools.chain(media_type_map.values(), (MediaType.UNKNOWN,))
            }
            post = media_post['post']
            post['teaser'] = Teaser(post['teaser'])

            for idx, media in enumerate(media_post['media']):
                media['type'] = media_type_map.get(media['type'], MediaType.UNKNOWN)
                media['idx'] = next(media_type_counters[media['type']])

                if media['type'] == MediaType.AUDIO:
                    media['url'] += post['signedQuery']

                yield {'post': post, **media}


@dataclass
class Filter:
    limit: t.Optional[int] = None
    offset: t.Optional[t.Union[str, int]] = None
    only_allowed: t.Optional[bool] = None
    start_date: InitVar[t.Optional[date]] = None
    end_date: InitVar[t.Optional[date]] = None
    from_ts: t.Optional[int] = field(init=False)
    to_ts: t.Optional[int] = field(init=False)

    def __post_init__(
        self,
        start_date: t.Optional[date],
        end_date: t.Optional[date],
    ) -> None:
        self.from_ts = to_timestamp(start_date, time())
        self.to_ts = to_timestamp(end_date, time(23, 59, 59))

    def to_dict(self, remap_keys: t.Optional[t.Dict[str, str]] = None) -> t.Dict[str, t.Any]:
        remap_keys = remap_keys or {}
        return {
            remap_keys.get(k, k): v if isinstance(v, str) else json.dumps(v)
            for k, v in asdict(self).items()
            if v is not None
        }


class Post(UserDict):
    def _get_datetime(self, key) -> t.Optional[datetime]:
        if key in self.data:
            return datetime.fromtimestamp(self.data[key])
        return None

    @cached_property
    def content(self) -> t.Sequence[t.Dict[str, t.Any]]:
        """Extracts content from a list with styles for Boosty."""
        return extract_content(self.data['data'])

    @cached_property
    def created_at(self) -> t.Optional[datetime]:
        return self._get_datetime('createdAt')

    @cached_property
    def publish_time(self) -> t.Optional[datetime]:
        return self._get_datetime('publishTime')

    @cached_property
    def teaser(self) -> 'Teaser':
        return Teaser(self.data.get('teaser', []))

    @cached_property
    def text_content(self) -> str:
        """Extracts text from a list with styles for Boosty."""
        return extract_text(self.data['data'])

    @cached_property
    def updated_at(self) -> t.Optional[datetime]:
        return self._get_datetime('updatedAt')

    def iter_media(self, media_type: MediaType = MediaType.ALL):
        for content in self.data['data']:
            content_type = MEDIA_TYPE_MAP.get(content['type'])
            if content_type and (media_type == MediaType.ALL or media_type == content_type):
                yield content

    def get_media(self, media_type: MediaType = MediaType.ALL):
        return list(self.iter_media(media_type))


@dataclass
class Teaser:
    input_data: InitVar[t.Sequence[t.Dict[str, t.Any]]]
    description: str = field(default='', init=False)
    images: t.Sequence[t.Dict[str, t.Any]] = field(default_factory=list, init=False)

    def __post_init__(self, input_data: t.Sequence[t.Dict[str, t.Any]]) -> None:
        self.description = extract_text(input_data)
        self.images = extract_images(input_data)

    def get_thumbnail(self, default: str = '') -> str:
        return self.images[0]['url'] if len(self.images) > 0 else default
