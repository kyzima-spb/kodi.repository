import datetime

class safe_datetime(datetime.datetime):
    @classmethod
    def strptime(cls, date_string, format): ...
