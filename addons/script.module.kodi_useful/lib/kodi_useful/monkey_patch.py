import datetime
from email.utils import parsedate_tz
import time


class safe_datetime(datetime.datetime):
    @classmethod
    def strptime(cls, date_string, format):
        try:
            return datetime.datetime(*(time.strptime(date_string, format)[:6]))
        except ValueError:
            parsed = parsedate_tz(date_string)

            if parsed:
                return datetime.datetime(*parsed[:6])
            else:
                raise ValueError("parsedate_tz returned None")


if not issubclass(datetime.datetime, safe_datetime):
    datetime.datetime = safe_datetime
