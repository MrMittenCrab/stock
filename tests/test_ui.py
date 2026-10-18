from stock.core import Store, State
from stock.ui import PriceApp, chart

ROWS=[dict(timestamp=f'2026-08-{i:02}T00:00:00Z',close=str(400+i),open='400',high='430',low='390',volume=100) for i in range(1,22)]

async def test_keyboard_edit_and_rows(tmp_path):
 store=Store(tmp_path/'db');app=PriceApp('700.HK',{'currency':'HKD'},ROWS,store,None,False)
 async with app.run_test(size=(90,35)) as pilot:
  await pilot.press('left');anchor=app.state.selected['timestamp']
  await pilot.press('down','down','right')
  assert app.state.row==2 and app.state.level==4
  assert app.state.selected['timestamp']==anchor
  await pilot.press('a','h','i','space','x','escape')
  assert store.annotations('700.HK')[anchor]=='hi x'
  await pilot.press('right')
  assert app.editing
  await pilot.press('left','space','escape')
  assert store.annotations('700.HK')[anchor]=='hi  x'

def test_chart_uses_observations():
 text=chart(State(ROWS),{},70,10)
 assert '▲' in text and 'AUG 2026' in text and '│' in text

async def test_zoom_resolution_preserves_hk_date_and_point(tmp_path):
 # Daily bars are stamped at HK midnight, on the previous UTC date.
 daily=[dict(timestamp='2026-08-13T16:00:00Z',close='400')]
 minutes=[dict(timestamp='2026-08-14T01:30:00Z',close='401'),
          dict(timestamp='2026-08-14T01:31:00Z',close='402')]
 class History:
  notices=set()
  def history(self,*args): return minutes
 app=PriceApp('700.HK',{'currency':'HKD'},daily,Store(tmp_path/'db'),History(),True)
 async with app.run_test(size=(80,30)):
  app.state.level=4
  await app.change_zoom(1)
  assert app.state.level==5
  assert app.timestamp()==daily[0]['timestamp']
  await app.change_zoom(-1)
  assert app.state.selected['timestamp']==daily[0]['timestamp']


def test_hk_midnight_annotation_marker():
 state=State([dict(timestamp='2026-08-13T16:00:00Z',close='400'),
              dict(timestamp='2026-08-14T16:00:00Z',close='405')])
 text=chart(state,{'2026-08-14T01:30:00Z':'note'},70,10)
 assert '●' in text
