import pytest
from stock.core import Store, State
from stock.ui import PriceApp, chart

ROWS=[dict(timestamp=f'2026-08-{i:02}T00:00:00Z',close=str(400+i),open='400',high='430',low='390',volume=100) for i in range(1,22)]

@pytest.mark.parametrize('width', [38, 70, 110])
def test_chart_marker_clearance_and_mapping(width):
 state=State(ROWS);state.index=10
 annotations={r['timestamp']:'note' for r in ROWS}
 lines=chart(state,annotations,width,10).splitlines()
 axis=next(i for i,line in enumerate(lines) if '└' in line)
 marks=lines[axis-1]
 assert '▼' in marks and '●' in marks
 assert set(marks[11:]) <= {' ', '▼', '●'}
 assert not any('●' in line or '▼' in line or '•' in line for line in lines[:axis-1])
 assert len(lines)==axis+2
 assert max(map(len,lines))<=width
 rows,_=state.window()
 from datetime import datetime
 times=[datetime.fromisoformat(r['timestamp'].replace('Z','+00:00')).timestamp() for r in rows]
 w=len(lines[axis])-11
 expected=round((times[10]-times[0])/(times[-1]-times[0])*(w-1))
 assert marks.index('▼')==11+expected

@pytest.mark.parametrize('values', [[1,10,1,10], [5,5,5], [2], list(range(100)), [1,10]*80])
def test_chart_is_one_connected_line(values):
 rows=[dict(timestamp=f'2026-08-01T00:{i//60:02}:{i%60:02}Z',close=str(v)) for i,v in enumerate(values)]
 state=State(rows);state.level=0
 lines=chart(state,{},40,8).splitlines()
 axis=next(i for i,line in enumerate(lines) if '└' in line)
 cells={(x,y) for y,line in enumerate(lines[:axis-1]) for x,c in enumerate(line[11:]) if c!=' '}
 assert cells
 seen={next(iter(cells))};pending=list(seen)
 while pending:
  x,y=pending.pop()
  for p in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
   if p in cells and p not in seen: seen.add(p);pending.append(p)
 assert seen==cells
 assert all(not set(line[11:]) & set('•┬┴├┤┼') for line in lines[:axis-1])

async def test_keyboard_edit_and_rows(tmp_path):
 store=Store(tmp_path/'db');app=PriceApp('700.HK',{'currency':'HKD'},ROWS,store,None,False)
 async with app.run_test(size=(90,35)) as pilot:
  await pilot.press('left');anchor=app.state.selected['timestamp']
  await pilot.press('down','right','right','h','i','space','x','left','space','up')
  assert not app.editing and app.state.row==0
  assert Store(tmp_path/'db').annotations('700.HK')[anchor]=='hi  x'
  await pilot.press('down','right')
  assert app.query_one('#annotation').display
  assert str(app.query_one('#annotation').render()).startswith('> '+' '*9)
  await pilot.press('end','!','down')
  assert not app.editing and app.state.row==2
  assert store.annotations('700.HK')[anchor]=='hi  x!'
  await pilot.press('left','right')
  assert app.state.selected['timestamp']==anchor
  await pilot.press('a','end','?','escape')
  assert not app.is_running
 assert Store(tmp_path/'db').annotations('700.HK')[anchor]=='hi  x!?'

async def test_layout_zoom_arrows_and_expansion(tmp_path):
 store=Store(tmp_path/'db');store.annotate('700.HK',ROWS[-1]['timestamp'],'Title\n'+'Long text '*40)
 app=PriceApp('700.HK',{'currency':'HKD'},ROWS,store,None,False)
 async with app.run_test(size=(80,30)) as pilot:
  def zoom(): return str(app.query_one('#zoom').render())
  rendered=str(app.query_one('#chart').render()).splitlines()
  assert len(next(line for line in rendered if '└' in line)) == 78
  before=zoom();assert '—←' in before and '→1W' in before
  await pilot.press('down');assert zoom()==before
  collapsed=app.query_one('#zoom').region.y
  await pilot.press('space');await pilot.pause()
  assert app.query_one('#zoom').virtual_region.y>collapsed
  await pilot.press('down');assert zoom().replace('>',' ',1)==before
  await pilot.press('right');assert '→—' in zoom()
  await pilot.resize_terminal(50,24)
  await pilot.pause()
  resized=str(app.query_one('#chart').render()).splitlines()
  assert len(next(line for line in resized if '└' in line)) == 48
  annotation=str(app.query_one('#annotation').render()).splitlines()
  assert all(line.startswith(' '*11) for line in annotation)
  assert app.query_one('#annotation').virtual_region.bottom == app.query_one('#zoom').virtual_region.y

async def test_zoom_resolution_preserves_hk_date_and_point(tmp_path):
 daily=[dict(timestamp='2026-08-13T16:00:00Z',close='400')]
 minutes=[dict(timestamp='2026-08-14T01:30:00Z',close='401'),dict(timestamp='2026-08-14T01:31:00Z',close='402')]
 class History:
  notices=set()
  def history(self,*args): return minutes
 app=PriceApp('700.HK',{'currency':'HKD'},daily,Store(tmp_path/'db'),History(),True)
 async with app.run_test(size=(80,30)):
  app.state.level=4
  await app.change_zoom(1)
  assert app.state.level==5 and app.timestamp()==daily[0]['timestamp']
  await app.change_zoom(-1)
  assert app.state.selected['timestamp']==daily[0]['timestamp']

def test_hk_midnight_annotation_marker():
 state=State([dict(timestamp='2026-08-13T16:00:00Z',close='400'),dict(timestamp='2026-08-14T16:00:00Z',close='405')])
 assert '●' in chart(state,{'2026-08-14T01:30:00Z':'note'},70,10)


def test_irregular_timestamps_share_marker_scale():
 rows=[dict(timestamp=t,close=str(v)) for t,v in [
  ('2026-08-01T00:00:00Z',1),('2026-08-02T00:00:00Z',2),('2026-08-21T00:00:00Z',3)]]
 state=State(rows);state.index=1
 lines=chart(state,{rows[1]['timestamp']:'selected note'},71,6).splitlines()
 axis=next(i for i,line in enumerate(lines) if '└' in line)
 assert lines[axis-1].index('▼') == 11+round(59/20)
 assert '●' not in lines[axis-1]
 state.move(1)
 updated=chart(state,{rows[1]['timestamp']:'note'},71,6).splitlines()
 assert updated[axis-1].index('●') == 11+round(59/20)
 assert updated[axis-1].index('▼') == 70


async def test_zoom_failure_and_available_resolution(tmp_path):
 from stock.data import DataError
 class History:
  notices=set()
  def history(self,*args): raise DataError('History unavailable')
 app=PriceApp('700.HK',{'currency':'HKD'},ROWS,Store(tmp_path/'db'),History(),'5m')
 async with app.run_test(size=(80,30)):
  app.state.level=4
  anchor=app.timestamp()
  assert app.state.zooms[5:]==[('1D','5m',66),('1H','5m',12)]
  await app.change_zoom(1)
  assert app.state.level==4 and app.timestamp()==anchor and not app.loading
  assert 'History unavailable' in str(app.query_one('#status').render())
