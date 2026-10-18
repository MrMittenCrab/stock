"""Exchange conventions; calendars and observations come from Longbridge."""
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Exchange:
    market: str
    currency: str
    timezone: ZoneInfo
    session_minutes: int

    def date(self, timestamp):
        return datetime.fromisoformat(timestamp.replace('Z', '+00:00')).astimezone(self.timezone).date()


EXCHANGES = {
    'HK': Exchange('HK', 'HKD', ZoneInfo('Asia/Hong_Kong'), 330),
    'US': Exchange('US', 'USD', ZoneInfo('America/New_York'), 390),
}


def exchange(ticker):
    return EXCHANGES[ticker.rsplit('.', 1)[1]]
