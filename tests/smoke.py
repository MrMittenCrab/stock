"""Fresh authenticated, read-only US/HK smoke: python tests/smoke.py."""
import json
from stock.core import Store
from stock.data import Market
from stock.exchanges import exchange


class FreshMarket(Market):
 def fetch(self,method,params,ttl=0):
  # Bypass the persistent cache completely: stale data cannot pass this smoke.
  result=self.rpc.call(method,params)
  self.store.put(method+json.dumps(params,sort_keys=True),result)
  return result


def main():
 market=FreshMarket(Store())
 try:
  for name,ticker in [('coreweave','CRWV.US'),('tencent','700.HK')]:
   matches=market.search(name)
   assert any(t==ticker for t,_ in matches)
   if ticker=='CRWV.US':assert matches[0][0]==ticker
   info=market.metadata(ticker);assert info['currency']==exchange(ticker).currency
   daily=market.history(ticker);period=market.finest(ticker)
   minute=market.history(ticker,period)
   calendar=market.calendar(daily[-21:],ticker)
   anchored=market.history(ticker,period,daily[-1]['timestamp'])
   assert any(exchange(ticker).date(r['timestamp'])==exchange(ticker).date(daily[-1]['timestamp']) for r in anchored)
   print(f"PASS · {ticker} · {info['currency']} · {name} matches {len(matches)}",flush=True)
   print(f"Daily {len(daily)} · {daily[0]['timestamp']} → {daily[-1]['timestamp']}",flush=True)
   print(f"{period} {len(minute)} · anchored {len(anchored)} · calendar {len(calendar['trading_days'])} days",flush=True)
  calendars={m:market.fetch('quote.trading_days',{'market':m,'start':'2026-07-01','end':'2026-07-07'}) for m in ('US','HK')}
  assert '2026-07-01' in calendars['US']['trading_days'] and '2026-07-01' not in calendars['HK']['trading_days']
  assert '2026-07-03' in calendars['HK']['trading_days'] and '2026-07-03' not in calendars['US']['trading_days']
  print('PASS · independent HK July 1 / US July 3 holiday calendars',flush=True)
  if market.notices:raise RuntimeError(str(market.notices))
 finally:market.rpc.close()


if __name__=='__main__':main()
