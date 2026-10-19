import json
import sqlite3
from pathlib import Path
from unittest.mock import Mock
import pytest
from stock.core import Store
from stock.archive import import_document, documents
from stock import sources
from stock.sort import units, validate, public_date, sort_document, sort_stock, Cursor, original_match
from stock.sources_ui import SourcesApp, passage_lines

QUOTE='Demand is growing across our markets, and we are expanding our capacity.'

@pytest.fixture
def fixture(tmp_path,monkeypatch):
 import stock.archive as archive
 monkeypatch.setattr(archive,'ROOT',tmp_path)
 p=tmp_path/'source.md';p.write_text('# Investor Presentation\n\nAlice Executive\n\n'+QUOTE+'\n')
 store=Store(tmp_path/'db')
 doc=import_document(store,'CRWV.US',p)
 sources.schema(store)
 return store,doc


def raw(text=QUOTE,topics=None):
 return dict(text=text,category='Management',speaker='Alice Executive',speaker_evidence='Alice Executive',topics=topics if topics is not None else ['Market','Operations'])


def seed(fixture):
 store,doc=fixture
 cursor=Mock();cursor.extract.return_value=[raw()]
 sort_document(store,doc,cursor,lambda _:None)
 return store,doc,sources.passages(store,'CRWV.US')[0]


def test_frozen_skip_manual_reset(fixture,monkeypatch):
 store,doc,p=seed(fixture)
 before=store.db.execute('SELECT * FROM source_passages').fetchall()
 sources.set_topic(store,p['id'],'Market',False)
 sources.set_topic(store,p['id'],'Capital',True)
 monkeypatch.setattr('stock.sort.Cursor',Mock(side_effect=AssertionError('Must not call Cursor')))
 progress=[]
 assert sort_stock(store,'CRWV.US',progress.append)
 assert 'Already sorted' in progress[0]
 assert sources.passages(store,'CRWV.US')[0]['topics']=={'Operations','Capital'}
 sources.reset(store,'CRWV.US',str(doc['id']))
 assert sources.passages(store,'CRWV.US')[0]['topics']=={'Market','Operations'}
 assert before==store.db.execute('SELECT * FROM source_passages').fetchall()
 assert store.db.execute('SELECT COUNT(*) FROM source_overrides').fetchone()[0]==0
 sources.reset(store,'CRWV.US',Path(doc['original']).name)
 with pytest.raises(ValueError): sources.reset(store,'700.HK',str(doc['id']))


def test_failed_and_interrupted_atomicity(fixture):
 store,doc=fixture
 cursor=Mock();cursor.extract.return_value=[raw(),raw('Invented quotation that does not exist in the document.')]
 with pytest.raises(ValueError,match='exact'): sort_document(store,doc,cursor,lambda _:None)
 assert not sources.completed(store,doc['id'])
 assert not sources.passages(store,'CRWV.US')
 cursor.extract.side_effect=KeyboardInterrupt
 with pytest.raises(KeyboardInterrupt): sort_document(store,doc,cursor,lambda _:None)
 assert not sources.completed(store,doc['id'])
 store.annotate('CRWV.US','test','Existing annotation')
 p=validate(raw(),dict(text=Path(doc['original']).read_text(),start=0,page=None,section=None),'',doc,None,'original text',doc['source_sha256'])
 # Fail after passage insertion, before completion: SQLite must roll back both.
 store.db.execute("CREATE TRIGGER fail_sort BEFORE INSERT ON source_sorts BEGIN SELECT RAISE(ABORT,'interrupted'); END")
 with pytest.raises(sqlite3.Error): sources.publish(store,doc,[p],doc['source_sha256'])
 assert not sources.passages(store,'CRWV.US')
 assert not sources.completed(store,doc['id'])
 assert store.annotations('CRWV.US')=={'test':'Existing annotation'}
 assert len(documents(store,'CRWV.US'))==1


def test_dates_require_public_provenance():
 d={'publication_date':'2025-05-07','metadata_provenance':json.dumps({'date':{'source':'user-supplied'}})}
 assert public_date(d)[0] is None
 d['metadata_provenance']=json.dumps({'date':{'basis':'Event date printed on transcript','url':'https://issuer.test'}})
 assert public_date(d)[0] is None
 d['metadata_provenance']=json.dumps({'date':{'basis':'Earliest independently verified public availability on SEC EDGAR','evidence_url':'https://sec.test'}})
 assert public_date(d)[0]=='2025-05-07'


@pytest.mark.parametrize('change',[{'category':'Executive'},{'topics':['Ideas']},{'topics':['Market','Market']},{'speaker':'Invented Person'},{'speaker_evidence':'made up'},{'text':'A completely invented original passage that is not in the source.'}])
def test_strict_validation(fixture,change):
 _,doc=fixture
 u=dict(text=Path(doc['original']).read_text(),start=0,page=None,section='Commentary')
 candidate=raw();candidate.update(change)
 with pytest.raises(ValueError): validate(candidate,u,'',doc,None,'original text','hash')


def test_pdf_verification_exact_original():
 page='Sales grew by $40 billion\nwith strong demand across all markets.'
 quote='Sales grew by \\$40 billion with strong demand across all markets.'
 assert original_match(quote,[page])==(1,0,len(page),page)
 with pytest.raises(ValueError): original_match('Sales grew by $50 billion with strong demand.',[page])
 with pytest.raises(ValueError): original_match(quote,[page,page])


def test_bounded_sections_no_gaps_or_overlap():
 text=''.join(f'# Section {i}\n\n'+('Commentary sentence. '*200)+'\n\n' for i in range(40))
 work=list(units(text))
 assert ''.join(u['text'] for u in work)==text
 assert max(len(u['text']) for u in work)<=18000
 assert len(work)<20
 for u in work: assert text[u['start']:u['start']+len(u['text'])]==u['text']
 giant='one long paragraph '*5000
 assert ''.join(u['text'] for u in units(giant))==giant


def test_cursor_actual_flags_and_json_validation(monkeypatch):
 monkeypatch.setattr('stock.sort.shutil.which',lambda _: '/usr/local/bin/agent')
 def run(cmd,**kw):
  if cmd[-1]=='--help': return Mock(returncode=0,stdout='--mode read-only --output-format --workspace --trust')
  if cmd[-1]=='status': return Mock(returncode=0,stdout='Logged in',stderr='')
  assert '--mode' in cmd and cmd[cmd.index('--mode')+1]=='ask'
  assert cmd[cmd.index('--output-format')+1]=='json'
  assert not any(flag in cmd for flag in ('--force','--yolo','--approve-mcps'))
  assert 'UNTRUSTED DATA' in cmd[-1]
  assert Path(kw['cwd']).is_dir()
  config=json.loads((Path(kw['cwd'])/'.cursor/cli.json').read_text())
  assert 'Shell(*)' in config['permissions']['deny'] and not config['permissions']['allow']
  return Mock(returncode=0,stdout=json.dumps({'type':'result','result':json.dumps({'passages':[raw()]})}))
 monkeypatch.setattr('stock.sort.subprocess.run',run)
 cursor=Cursor()
 assert cursor.extract({'text':QUOTE},'')==[raw()]
 monkeypatch.setattr('stock.sort.subprocess.run',lambda *a,**kw:Mock(returncode=0,stdout='{"type":"result","result":"invalid"}'))
 with pytest.raises(ValueError,match='structured output'): cursor.extract({'text':QUOTE},'')


def test_cursor_missing_and_unauthenticated(monkeypatch):
 monkeypatch.setattr('stock.sort.shutil.which',lambda _:None)
 with pytest.raises(ValueError,match='missing'): Cursor()
 monkeypatch.setattr('stock.sort.shutil.which',lambda _:'agent')
 monkeypatch.setattr('stock.sort.subprocess.run',lambda cmd,**kw: Mock(returncode=0,stdout='--mode read-only --output-format --workspace --trust' if cmd[-1]=='--help' else 'Not logged in',stderr=''))
 with pytest.raises(ValueError,match='unauthenticated'): Cursor()


async def test_sources_inline_filter_topics_source(fixture,monkeypatch):
 store,doc,p=seed(fixture)
 opened=[];monkeypatch.setattr('stock.sources_ui.open_file',lambda path:opened.append(path))
 app=SourcesApp('CRWV.US',store)
 async with app.run_test(size=(80,28)) as pilot:
  await pilot.press('right','space')
  assert app.topic=='Market' and p['id'] in app.expanded
  rendered=[str(w.render()) for w in app.row_widgets]
  assert rendered[0].count('Demand')==1
  assert all(line.startswith(' '*27) for line in rendered[0].splitlines()[1:])
  await pilot.press('t')
  assert str(app.row_widgets[1].render()).startswith('> [x] Market')
  await pilot.press('space')
  assert p['id']==app.editing and len(app.visible())==1
  assert 'Market' not in sources.passages(store,'CRWV.US')[0]['topics']
  await pilot.press('t')
  assert len(app.visible())==0
  await pilot.press('left','down','down','right','o')
  assert app.topic=='Operations' and opened==[doc['original']]
  assert 'Unknown' in app.message and 'Characters' in app.message
  await pilot.press('f','down','right')
  assert app.document_id==doc['id'] and not app.files
  await pilot.press('space')
  await pilot.resize_terminal(52,20)
  await pilot.pause()
  lines=passage_lines(app.visible()[0],50,True)
  assert max(map(len,lines))<=50
  assert all(line.startswith(' '*27) for line in lines[1:])
  await pilot.press('escape')
 assert not app.is_running


def test_unknown_dates_after_known(fixture):
 store,doc=fixture
 source=Path(doc['original']).read_text()
 p=validate(raw(),dict(text=source,start=0,page=None,section=None),'',doc,None,'original text','hash')
 p2={**p,'text':'Another original passage', 'location':{'start':99},'publication_date':'2025-01-01'}
 sources.publish(store,doc,[p,p2],doc['source_sha256'])
 rows=sources.passages(store,'CRWV.US')
 assert rows[0]['publication_date']=='2025-01-01'
 assert rows[1]['publication_date'] is None

@pytest.mark.parametrize('markdown',['missing','converted'])
def test_pdf_only_and_conversion_failed(fixture,tmp_path,monkeypatch,markdown):
 store,doc=fixture
 original=tmp_path/'original.pdf';original.write_bytes(Path(doc['original']).read_bytes())
 doc={**doc,'original':str(original),'markdown':doc['markdown'] if markdown=='converted' else str(tmp_path/'missing.md'),'conversion_status':'failed' if markdown=='missing' else 'converted'}
 monkeypatch.setattr('stock.sort.pdf_pages',lambda _:[original.read_text()])
 cursor=Mock();cursor.extract.return_value=[raw()]
 assert sort_document(store,doc,cursor,lambda _:None)==1
 p=sources.passages(store,'CRWV.US')[0]
 assert p['text']==QUOTE and p['location']['page']==1
 assert 'PDF' in p['location']['kind']
 assert sources.completed(store,doc['id'])


def test_multiple_speakers_and_zero_topics(fixture):
 store,doc=fixture
 text='Alice Executive: '+QUOTE+'\nReporter Jane: Competition is increasing across the entire industry.'
 u=dict(text=text,start=0,page=None,section=None)
 p1=validate(raw(),u,'',doc,None,'original text','hash')
 p2=validate(dict(text='Competition is increasing across the entire industry.',category='Media',speaker='Reporter Jane',speaker_evidence='Reporter Jane',topics=[]),u,'',doc,None,'original text','hash')
 sources.publish(store,doc,[p1,p2],doc['source_sha256'])
 rows=sources.passages(store,'CRWV.US')
 assert {p['category'] for p in rows}=={'Management','Media'}
 assert next(p for p in rows if p['category']=='Media')['topics']==set()


def test_source_change_while_running_does_not_publish(fixture):
 store,doc=fixture
 def extract(*args):
  Path(doc['original']).write_text('changed')
  return [raw()]
 cursor=Mock();cursor.extract.side_effect=extract
 with pytest.raises(ValueError,match='changed during sorting'): sort_document(store,doc,cursor,lambda _:None)
 assert not sources.completed(store,doc['id'])
 assert not sources.passages(store,'CRWV.US')


def test_pdf_pages_batched_with_exact_page_offsets(fixture):
 from stock.sort import pdf_units
 _,doc=fixture
 pages=['Cover text\n','Alice Executive\n'+QUOTE,'No substantive commentary here.']
 work=list(pdf_units(pages))
 assert len(work)==1
 p=validate(raw(),work[0],'',doc,pages,'PDF text (Markdown unavailable)','hash')
 loc=p['location']
 assert loc['page']==2
 assert pages[1][loc['start']:loc['end']]==QUOTE
 large=list(pdf_units([QUOTE*50 for _ in range(100)]))
 assert len(large)<30
 assert all(len(u['text'])<=18000 for u in large)


def test_conversion_typography_keeps_exact_pdf(fixture):
 _,doc=fixture
 original='Our “AI platform” generated $40 billion\nin committed contracts.'
 markdown='Our **"AI platform"** generated \\$40 billion in committed contracts.'
 u=dict(text=markdown,start=0,page=None,section=None)
 r=raw('Our "AI platform" generated $40 billion in committed contracts.')
 r.update(speaker=None,speaker_evidence=None)
 p=validate(r,u,'',doc,[original],'converted Markdown','hash')
 assert p['text']==original
 assert p['location']['page']==1
 changed=dict(r,text='Our "AI platform" generated $50 billion in committed contracts.')
 with pytest.raises(ValueError): validate(changed,u,'',doc,[original],'converted Markdown','hash')


async def test_long_expansion_can_scroll_and_reopen_topics(fixture):
 store,doc=fixture
 text=QUOTE+'\n'+'Original commentary with a long explanation. '*200
 p=dict(text=text,category='Management',speaker=None,location={'start':0,'end':len(text)},publication_date=None,date_provenance={},topics=['Market'])
 sources.publish(store,doc,[p],doc['source_sha256'])
 app=SourcesApp('CRWV.US',store)
 async with app.run_test(size=(80,24)) as pilot:
  await pilot.press('right','space')
  assert app.query_one('#rows').max_scroll_y>0
  await pilot.press('pagedown');await pilot.pause()
  assert app.query_one('#rows').scroll_y>0
  await pilot.press('t');await pilot.pause()
  assert app.editing and any('[x] Market' in str(w.render()) for w in app.row_widgets)
  await pilot.press('escape')


def test_adjacent_page_narrative_keeps_verifiable_segments(fixture):
 from stock.sort import original_fragments
 _,doc=fixture
 first='Before we discuss our outlook, we have expanded our capacity and committed resources to '
 last='deliver better execution and provide our customers with more reliable services.'
 pages=['HEADER\n'+first,'REPEATED HEADER\n'+last+'\nFollowing paragraph.']
 quote=first+last
 fragments=original_fragments(quote,pages)
 assert len(fragments)==2
 r=raw(quote);r.update(speaker=None,speaker_evidence=None)
 p=validate(r,dict(text=quote,start=0,page=None,section=None),'',doc,pages,'converted Markdown','hash')
 assert p['location']['page']==1 and p['location']['page_end']==2
 assert 'HEADER' not in p['text']
 for segment in p['location']['segments']:
  assert pages[segment['page']-1][segment['start']:segment['end']]==p['text'][segment['text_start']:segment['text_end']]
 with pytest.raises(ValueError): original_fragments(quote.replace('better execution','invented execution'),pages)


def test_line_end_hyphenation_preserves_original_pdf(fixture):
 _,doc=fixture
 page='Demand remains strong for near-\nterm capacity across all of our markets.'
 quote='Demand remains strong for nearterm capacity across all of our markets.'
 r=raw(quote);r.update(speaker=None,speaker_evidence=None)
 p=validate(r,dict(text=quote,start=0,page=None,section=None),'',doc,[page],'converted Markdown','hash')
 assert p['text']==page
