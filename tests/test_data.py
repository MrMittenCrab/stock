import pytest
from stock.core import Store
from stock.data import Market, DataError, RPC

class Unavailable:
 def call(self,*args): raise DataError('offline')

def test_offline_cache_and_missing_history(tmp_path):
 store=Store(tmp_path/'db');market=Market(store,Unavailable())
 store.put('quote.static_info{"symbols": ["700.HK"]}',[{'symbol':'700.HK','currency':'HKD'}])
 assert market.fetch('quote.static_info',{'symbols':['700.HK']},ttl=-1)[0]['currency']=='HKD'
 assert any('OFFLINE' in n for n in market.notices)
 with pytest.raises(DataError,match='offline'): market.history('700.HK')

def test_reject_trade_methods():
 with pytest.raises(DataError,match='read-only'): RPC().call('trade.submit_order',{})

def test_search_normalizes_filters_and_matches(tmp_path):
 class Catalogue:
  def call(self,*args):
   return [{'symbol':'00700.HK','name_en':'TENCENT','name_cn':'腾讯控股'},
           {'symbol':'AAPL.US','name_en':'Apple'}]
 market=Market(Store(tmp_path/'db'),Catalogue())
 assert market.search('Tencent')[0][0]=='700.HK'
 assert market.search('00700')[0][0]=='700.HK'
 assert market.search('Apple')[0][0]=='AAPL.US'

def test_calendar_chunks_upstream_month_limit(tmp_path):
 from datetime import date
 class Calendar:
  def call(self,method,params):
   assert (date.fromisoformat(params['end'])-date.fromisoformat(params['start'])).days<=27
   return {'trading_days':[params['start']], 'half_trading_days':[]}
 market=Market(Store(tmp_path/'db'),Calendar())
 result=market.calendar([{'timestamp':'2026-08-01T00:00:00Z'},{'timestamp':'2026-10-01T00:00:00Z'}])
 assert len(result['trading_days'])==3

def test_finest_resolution_uses_successful_observations(tmp_path):
 class Entitled:
  def call(self,method,params):
   if params['period']=='1m': raise DataError('not entitled')
   return [dict(timestamp='2026-08-14T01:30:00Z',open='4',high='4',low='4',close='4',volume=1)]
 market=Market(Store(tmp_path/'db'),Entitled())
 assert market.finest('700.HK')=='5m'
