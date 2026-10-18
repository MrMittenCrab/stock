"""Explicit live read-only smoke: python tests/smoke.py (requires authentication)."""
from stock.core import Store
from stock.data import Market

class FreshMarket(Market):
 def fetch(self,method,params,ttl=0):
  return super().fetch(method,params,ttl=0)

def main():
 market=FreshMarket(Store())
 try:
  info=market.metadata('700.HK');assert info['currency']=='HKD'
  matches=market.search('Tencent');assert any(t=='700.HK' for t,_ in matches)
  daily=market.history('700.HK');minute=market.history('700.HK','1m')
  calendar=market.calendar(daily[-21:])
  anchored=market.history('700.HK','1m',daily[-1]['timestamp'])
  print(f"PASS · 700.HK · {info['currency']} · Tencent matches {len(matches)}")
  print(f"Daily {len(daily)} · {daily[0]['timestamp']} → {daily[-1]['timestamp']}")
  print(f"1m {len(minute)} · anchored 1m {len(anchored)} · calendar fields {list(calendar)}")
  if market.notices: raise RuntimeError('Smoke used stale fallback: '+str(market.notices))
 finally: market.rpc.close()

if __name__=='__main__': main()
