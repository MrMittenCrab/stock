import pytest
from stock.core import symbol, Store, State

def test_symbols():
 assert symbol('00700.hk') == '700.HK'
 for bad in ['Tencent','700','0.HK','700.HK;ls']:
  with pytest.raises(ValueError): symbol(bad)

def test_annotation_persistence(tmp_path):
 p=tmp_path/'stock.db'
 s=Store(p);s.annotate('700.HK','2026-08-14T00:00:00Z','Demand concerns')
 assert Store(p).annotations('700.HK') == {'2026-08-14T00:00:00Z':'Demand concerns'}

def test_navigation_and_anchor():
 s=State([{'timestamp':str(i),'close':str(i)} for i in range(100)])
 s.move(-1); assert s.index==98
 anchor=s.selected['timestamp'];s.zoom(1)
 assert s.selected['timestamp']==anchor
 s.row=0;s.select_row(-1);assert s.row==0
 s.select_row(20);assert s.row==2

def test_cache_and_errors(tmp_path):
 s=Store(tmp_path/'s.db');assert s.get('missing') is None
 s.put('x',{'a':1});assert s.get('x')[0]=={'a':1}
 with pytest.raises(ValueError,match='No historical'): State([])
