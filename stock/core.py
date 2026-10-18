import json
import re
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / '.data' / 'stock.sqlite3'


def symbol(value):
    if not re.fullmatch(r'[0-9]{1,5}\.HK', value.upper()) or int(value.split('.')[0]) == 0:
        raise ValueError('Expected a Hong Kong ticker such as 700.HK; use stock search for names')
    return f"{int(value.split('.')[0])}.HK"


class Store:
    def __init__(self, path=DB):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, payload TEXT, updated REAL);
        CREATE TABLE IF NOT EXISTS annotations(symbol TEXT, timestamp TEXT, text TEXT,
          PRIMARY KEY(symbol,timestamp));
        ''')

    def get(self, key):
        row = self.db.execute('SELECT payload,updated FROM cache WHERE key=?', (key,)).fetchone()
        return (json.loads(row[0]), row[1]) if row else None

    def put(self, key, value):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?)',
                            (key, json.dumps(value), time.time()))

    def annotate(self, ticker, timestamp, text):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO annotations VALUES(?,?,?)', (ticker, timestamp, text))

    def annotations(self, ticker):
        return dict(self.db.execute('SELECT timestamp,text FROM annotations WHERE symbol=?', (ticker,)))


# Longest to shortest; daily windows then intraday windows, all observation-based.
ZOOMS = [('1Y', 'day', 252), ('6M', 'day', 126), ('3M', 'day', 63),
         ('1M', 'day', 21), ('1W', 'day', 5), ('1D', '1m', 330), ('1H', '1m', 60)]


class State:
    def __init__(self, observations):
        if not observations:
            raise ValueError('No historical observations available')
        self.observations = observations
        self.index = len(observations)-1
        self.row = 0
        self.level = 3
        self.zooms = list(ZOOMS)

    @property
    def selected(self):
        return self.observations[self.index]

    def move(self, direction):
        self.index = max(0, min(len(self.observations)-1, self.index+direction))

    def select_row(self, direction):
        self.row = max(0, min(2, self.row+direction))

    def zoom(self, direction):
        self.level = max(0, min(len(ZOOMS)-1, self.level+direction))

    def window(self):
        count = self.zooms[self.level][2]
        end = min(len(self.observations), max(self.index+1, self.index+count//2))
        start = max(0, end-count)
        return self.observations[start:end], start
