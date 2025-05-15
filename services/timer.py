from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


class Timer(object):
    def __init__(self):
        date = datetime.now(ZoneInfo("Europe/Stockholm"))
        self.start = date
        self.latest_update = datetime.min

    def set_latest_update(self, date_string):
        self.latest_update = datetime.strptime(
            date_string, "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=ZoneInfo("Europe/Stockholm"))

    def day_before(self):
        return str(self.latest_update - timedelta(days=1))

    def six_months_before(self):
        return str(self.latest_update - timedelta(days=180))

    def start_string(self):
        return self.start.strftime("%Y-%m-%d %H:%M:%S")

    def get_delta(self):
        delta = self.start - self.latest_update
        return delta.days
