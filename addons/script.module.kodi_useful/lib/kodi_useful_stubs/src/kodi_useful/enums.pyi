import enum

class Content(str, enum.Enum):
    ALBUMS = 'albums'
    ARTISTS = 'artists'
    EPISODES = 'episodes'
    GAMES = 'games'
    FILES = 'files'
    IMAGES = 'images'
    MOVIES = 'movies'
    MUSICVIDEOS = 'musicvideos'
    SONGS = 'songs'
    TVSHOWS = 'tvshows'
    VIDEOS = 'videos'

class Scope(enum.Enum):
    NOTSET = ...
    QUERY = ...
    SETTINGS = ...
