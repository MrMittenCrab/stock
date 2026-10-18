from datetime import datetime
import pytest
from stock.core import Store, symbol
from stock.data import Market, DataError
from stock.ui import PriceApp, date_label


def test_us_symbols_and_isolated_notes(tmp_path):
 assert symbol('crwv.us') == 'CRWV.US'
 assert symbol('brk.b.us') == 'BRK.B.US'
 s=Store(tmp_path/'db')
 s.annotate('crwv.us','2026-08-14T00:00:00Z','US')
 s.annotate('00700.hk','2026-08-14T00:00:00Z','HK')
 assert s.annotations('CRWV.US') == {'2026-08-14T00:00:00Z':'US'}
 assert list(s.annotations('700.HK').values()) == ['HK']


def test_both_catalogues_rank_and_deduplicate(tmp_path):
 class Catalogues:
  def call(self,method,p):
   return ([{'symbol':'CRWV.US','name_en':'CoreWeave, Inc.'},
            {'symbol':'OTHER.US','name_en':'CoreWeave Partners'},
            {'symbol':'CRWV.US','name_en':'CoreWeave, Inc.'}] if p['market']=='US' else
           [{'symbol':'00700.HK','name_en':'Tencent'}, {'symbol':'123.HK','name_en':'CoreWeave'}])
 m=Market(Store(tmp_path/'db'),Catalogues())
 assert m.search('CoReWeAvE')[0][0]=='123.HK'
 assert [x[0] for x in m.search('coreweave')].count('CRWV.US')==1
 assert m.search('crwv')[0][0]=='CRWV.US'
 assert m.search('tencent')[0][0]=='700.HK'


def test_us_history_dates_and_calendar(tmp_path):
 class API:
  def call(self,method,p):
   if method=='quote.trading_days':
    assert p['market']=='US' and p['start']=='2026-08-13'
    return {'trading_days':['2026-08-13'],'half_trading_days':[]}
   assert p['start']=='2026-08-06' and p['end']=='2026-08-14'
   return [dict(timestamp='2026-08-13T20:00:00Z',open='1',high='1',low='1',close='1',volume=1)]
 m=Market(Store(tmp_path/'db'),API())
 rows=m.history('CRWV.US','1m','2026-08-14T00:00:00Z')
 assert m.calendar(rows,'CRWV.US')['trading_days']==['2026-08-13']


def test_us_dst_labels():
 from zoneinfo import ZoneInfo
 ny=ZoneInfo('America/New_York')
 assert '09:30 EDT' in date_label('2026-08-14T13:30:00Z',True,ny)
 assert '09:30 EST' in date_label('2026-12-14T14:30:00Z',True,ny)


async def test_us_zoom_anchor_and_currency(tmp_path):
 daily=[dict(timestamp='2026-08-14T04:00:00Z',close='100')]
 class API:
  notices=set()
  def history(self,*a):return [dict(timestamp='2026-08-14T13:30:00Z',close='101')]
 app=PriceApp('CRWV.US',{'currency':'USD'},daily,Store(tmp_path/'db'),API(),'1m')
 async with app.run_test(size=(90,30)):
  assert app.state.zooms[5][2]==390
  assert 'CRWV.US · USD' in str(app.query_one('#heading').render())
  app.state.level=4
  await app.change_zoom(1)
  assert app.state.level==5 and app.timestamp()==daily[0]['timestamp']
  await app.change_zoom(-1)
  assert app.timestamp()==daily[0]['timestamp']


def test_short_history_limits_zoom(tmp_path):
 rows=[dict(timestamp=f'2026-08-{i:02}T04:00:00Z',close='100') for i in range(1,11)]
 app=PriceApp('CRWV.US',{'currency':'USD'},rows,Store(tmp_path/'db'),None,False)
 assert app.minimum_level==4 and app.state.level==4


def test_permission_error_is_contextual(tmp_path):
 class Denied:
  def call(self,*a): raise DataError('quote permission denied')
 m=Market(Store(tmp_path/'db'),Denied())
 with pytest.raises(DataError,match='CRWV.US.*day.*permission denied'):
  m.history('CRWV.US')


def test_permission_cache_notice_keeps_upstream_reason(tmp_path):
 class Denied:
  def call(self,*a): raise DataError('quote permission denied')
 store=Store(tmp_path/'db');m=Market(store,Denied())
 store.put('test{}',[1])
 assert m.fetch('test',{},ttl=-1)==[1]
 assert any('permission denied' in n for n in m.notices)


def test_duplicate_catalogue_keeps_best_name_rank(tmp_path):
 class API:
  def call(self,method,p):
   return [] if p['market']=='HK' else [
    {'symbol':'CRWV.US','name_en':'CoreWeave'},
    {'symbol':'OTHER.US','name_en':'CoreWeave Partners'},
    {'symbol':'CRWV.US','name_en':'Long CoreWeave Description'}]
 m=Market(Store(tmp_path/'db'),API())
 assert m.search('coreweave')[0][0]=='CRWV.US'


def test_missing_us_history_and_partial_search(tmp_path):
 class API:
  def call(self,method,p):
   if method=='quote.security_list':
    if p['market']=='HK':raise DataError('catalogue permission denied')
    return [{'symbol':'CRWV.US','name_en':'CoreWeave'}]
   return []
 m=Market(Store(tmp_path/'db'),API())
 with pytest.raises(DataError,match='No day history available for CRWV.US'):m.history('CRWV.US')
 assert m.search('coreweave')[0][0]=='CRWV.US'
 assert any('HK search unavailable' in n for n in m.notices)


def test_us_daily_marker_uses_new_york_date():
 from stock.core import State
 from stock.ui import chart
 from stock.exchanges import exchange
 rows=[dict(timestamp='2026-08-13T04:00:00Z',close='100'),dict(timestamp='2026-08-14T04:00:00Z',close='101')]
 state=State(rows)
 # UTC August 14 is still August 13 in New York.
 lines=chart(state,{'2026-08-14T00:00:00Z':'US note'},70,8,exchange('CRWV.US')).splitlines()
 assert lines[-3][11]=='●' and lines[-3].endswith('▼')
