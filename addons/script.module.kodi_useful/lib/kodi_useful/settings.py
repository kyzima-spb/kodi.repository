import configparser
from contextlib import suppress
import xbmcaddon


def get_boolean(key, addon_id=None):
    value = get_string(key, addon_id)
    with suppress(KeyError):
        value = configparser.ConfigParser.BOOLEAN_STATES[value]
    return bool(value)


def get_int(key, addon_id=None):
    return int(get_string(key, addon_id))


def get_string(key, addon_id=None):
    if addon_id is not None:
        return xbmcaddon.Addon(addon_id).getSetting(key)
    else:
        return xbmcaddon.Addon().getSetting(key)
