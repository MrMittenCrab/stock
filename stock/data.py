"""Read-only Longbridge JSON-RPC transport and persistent response cache."""
import json
import selectors
import subprocess
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from .core import symbol
from .exchanges import exchange
from difflib import SequenceMatcher
import re

HK = ZoneInfo('Asia/Hong_Kong')


def hk_date(timestamp):
    return datetime.fromisoformat(timestamp.replace('Z','+00:00')).astimezone(HK).date()


class DataError(Exception):
    pass


class RPC:
    def __init__(self):
        self.process = None
        self.serial = 0
        self.last = 0

    def call(self, method, params):
        if method not in {'quote.static_info', 'quote.candlesticks',
                          'quote.history_candlesticks_by_date', 'quote.trading_days',
                          'quote.trading_session', 'quote.security_list', 'api.get'}:
            raise DataError('Unsupported read-only method')
        if self.process is None:
            try:
                self.process = subprocess.Popen(['longbridge', 'serve'], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
            except OSError as e:
                raise DataError('Longbridge CLI unavailable; install longbridge and authenticate') from e
        # Conservative pacing: below 30 requests/30 seconds, including failed calls.
        time.sleep(max(0, 1.1-(time.monotonic()-self.last)))
        self.last = time.monotonic()
        self.serial += 1
        try:
            self.process.stdin.write(json.dumps(dict(jsonrpc='2.0', id=self.serial,
                                                     method=method, params=params))+'\n')
            self.process.stdin.flush()
            deadline = time.monotonic()+30
            with selectors.DefaultSelector() as selector:
                selector.register(self.process.stdout, selectors.EVENT_READ)
                while time.monotonic() < deadline:
                    if not selector.select(max(0, deadline-time.monotonic())):
                        break
                    line = self.process.stdout.readline()
                    if not line:
                        raise DataError('Longbridge disconnected; check longbridge auth status')
                    reply = json.loads(line)
                    if reply.get('id') != self.serial:
                        continue
                    if 'error' in reply:
                        raise DataError(reply['error'].get('message', 'Longbridge API error'))
                    return reply['result']
        except (OSError, ValueError, KeyError) as e:
            self.close()
            raise DataError('Invalid or unavailable Longbridge response') from e
        self.close()
        raise DataError('Longbridge timed out; check authentication or network')

    def close(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            for stream in (self.process.stdin, self.process.stdout):
                stream.close()
            self.process = None


class Market:
    def __init__(self, store, rpc=None):
        self.store = store
        self.rpc = rpc or RPC()
        self.notices = set()

    def fetch(self, method, params, ttl=3600):
        key = method+json.dumps(params, sort_keys=True)
        cached = self.store.get(key)
        if cached and time.time()-cached[1] < ttl:
            return cached[0]
        try:
            result = self.rpc.call(method, params)
            self.store.put(key, result)
            return result
        except DataError as e:
            if cached:
                date = datetime.fromtimestamp(cached[1], HK).strftime('%d %b %H:%M HKT')
                self.notices.add(f'OFFLINE · cached {date} · {e}')
                return cached[0]
            raise

    def metadata(self, ticker):
        ticker = symbol(ticker)
        result = self.fetch('quote.static_info', {'symbols':[ticker]}, 86400)
        if not result or result[0].get('symbol') != ticker:
            raise DataError(f'Unknown security: {ticker}')
        info = dict(result[0])
        expected = exchange(ticker).currency
        if info.get('currency') != expected:
            raise DataError(f'Unexpected currency for {ticker}: {info.get("currency")}')
        return info

    def history(self, ticker, period='day', anchor=None):
        ticker = symbol(ticker)
        if anchor:
            date = exchange(ticker).date(anchor)
            span = 400 if period == 'day' else 7
            params = {'symbol':ticker, 'period':period, 'adjust':'none',
                      'start':str(date-timedelta(days=span)), 'end':str(date+timedelta(days=span if period=='day' else 1))}
            method = 'quote.history_candlesticks_by_date'
        else:
            method = 'quote.candlesticks'
            params = {'symbol':ticker,'period':period,'count':1000,'adjust':'none'}
        try:
            result = self.fetch(method, params)
        except DataError as e:
            raise DataError(f'{ticker} · {period} history unavailable · {e}') from e
        rows = sorted({r['timestamp']:r for r in result}.values(), key=lambda r:r['timestamp'])
        if not rows:
            raise DataError(f'No {period} history available for {ticker}')
        for r in rows:
            if not all(k in r for k in ('open','high','low','close','volume','timestamp')):
                raise DataError('Incomplete OHLCV response')
            if not float(r['close']) > 0:
                raise DataError('Invalid historical close')
        return rows

    def finest(self, ticker):
        errors = []
        for period in ('1m', '5m', '15m', '30m', '1h'):
            try:
                self.history(ticker, period)
                return period
            except DataError as e:
                errors.append(f'{period}: {e}')
        raise DataError('Intraday unavailable · '+ '; '.join(errors))

    def calendar(self, observations, ticker='700.HK'):
        venue = exchange(symbol(ticker))
        start = venue.date(observations[0]['timestamp'])
        end = venue.date(observations[-1]['timestamp'])
        result = {'trading_days': [], 'half_trading_days': []}
        while start <= end:
            stop = min(end, start+timedelta(days=27))
            chunk = self.fetch('quote.trading_days',
                {'market':venue.market,'start':str(start),'end':str(stop)}, 86400)
            for key in result:
                result[key].extend(chunk.get(key, []))
            start = stop+timedelta(days=1)
        return {key:sorted(set(values)) for key,values in result.items()}

    def search(self, query):
        q = query.casefold().strip()
        if not q:
            return []
        matches = {}
        failures = []
        def clean(value):
            return ' '.join(re.findall(r'[^\W_]+', value.casefold()))
        for market in ('HK', 'US'):
            try:
                records = self.fetch('quote.security_list', {'market':market}, 86400)
            except DataError as e:
                failures.append(f'{market} search unavailable · {e}')
                continue
            for r in records:
                try:
                    ticker = symbol(r['symbol'])
                except (KeyError, ValueError):
                    continue
                if exchange(ticker).market != market:
                    continue
                names = list(dict.fromkeys(str(r[k]) for k in ('name_en','name_cn','name_hk') if r.get(k)))
                code = ticker.rsplit('.', 1)[0].casefold()
                exact = q in (ticker.casefold(), code)
                if market == 'HK' and q.removesuffix('.hk').isdigit():
                    exact = int(q.removesuffix('.hk')) == int(code)
                scores = []
                for name in [code] + names:
                    n, term = clean(name), clean(q)
                    if n == term: scores.append(1)
                    elif n.startswith(term): scores.append(2)
                    elif term in n: scores.append(3)
                    elif len(term) >= 4 and SequenceMatcher(None, term, n).ratio() >= .8:
                        scores.append(4)
                if exact or scores:
                    rank = 0 if exact else min(scores)
                    display = ' · '.join(names)
                    candidate = (rank, len(display), display)
                    matches[ticker] = min(candidate, matches.get(ticker, candidate))
        if failures:
            self.notices.update(failures)
            if len(failures) == 2:
                raise DataError('; '.join(failures))
        return [(ticker, matches[ticker][2]) for ticker in sorted(matches,
                key=lambda t:(matches[t][0], matches[t][1], t))]
