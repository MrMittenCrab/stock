"""Archive contracts: content evidence, immutable copies and persistent identity."""
import io
import json
from pathlib import Path
import pytest
from stock.core import Store
from stock import archive


def test_content_recognition_and_date_evidence():
    info = archive.identify('Tencent Holdings Limited\nAnnual Report 2025\nPublished: 19 March 2026\nPreviously published: 20 March 2026', {})
    assert info['type'] == 'Annual'
    assert info['period'] == 'FY2025'
    assert info['date'] == '2026-03-19'
    assert '19 March 2026' in json.dumps(info['date_evidence'])
    assert info['publisher'] == 'Tencent Holdings Limited'
    assert archive.basename(info) == '2026-03-19--annual--FY2025'


@pytest.mark.parametrize('text,kind,period', [
    ('Interim Results H1 2026\nFor the six months ended 30 June 2026','Interim','H1-2026'),
    ('Quarterly Report Q3 2025\nFor the quarter ended September 30, 2025','Quarterly','Q3-2025'),
    ('FORM 10-K\nFor the fiscal year ended December 31, 2025','Annual','FY2025'),
    ('Q2 2026 Earnings Call Transcript','Transcript','Q2-2026'),
    ('Equity Research\nGPU economics','Research',None),
    ('Letter to Shareholders','Letter',None),
])
def test_recognize_types_and_periods(text, kind, period):
    info=archive.identify(text,{})
    assert (info['type'],info['period']) == (kind,period)
    assert info['date'] is None


def test_dates_are_not_period_or_file_creation_dates():
    info=archive.identify('Annual Report 2025\nYear ended 31 December 2025\nBoard meeting 19 March 2026', {'creationDate':'D:20260319000000'})
    assert info['date'] is None
    assert archive.basename(info)=='undated--annual--FY2025'


def test_unknown_fields_prompt_and_all_types_available(monkeypatch):
    output=io.StringIO()
    answers=iter(['Research','','',''])
    info=archive.identify('GPU economics',{})
    archive.clarify(info,interactive=True,read=lambda _: next(answers),output=output)
    assert info['type']=='Research'
    assert 'Type?' in output.getvalue()
    assert 'Date?' not in output.getvalue()
    assert output.getvalue().count('?')==1
    assert all(t in output.getvalue() for t in archive.TYPES)
    with pytest.raises(ValueError,match='interactive|type'):
        archive.clarify(archive.identify('Ambiguous document',{}),interactive=False)


def test_import_dedup_collision_and_persistence(tmp_path):
    store=Store(tmp_path/'db')
    root=tmp_path/'Research'
    source=tmp_path/'misleading-annual-2026.md'
    source.write_text('# Interim Results H1 2026\nPublished: 2026-08-14\nPublisher: Example Inc.\nSix months ended 30 June 2026')
    result=archive.import_document(store,'00700.HK',source,root=root,interactive=False)
    assert Path(result['original']).name=='2026-08-14--interim--H1-2026.md'
    assert source.exists() and Path(result['original']).read_bytes()==source.read_bytes()
    assert result['sorted_at'] is None
    repeat=archive.import_document(store,'700.HK',source,root=root,interactive=False)
    assert repeat['id']==result['id']
    assert len(list((root/'700.HK'/'Archive').iterdir()))==1
    source.write_text(source.read_text()+'\nDifferent contents')
    other=archive.import_document(store,'700.HK',source,root=root,interactive=False)
    assert other['id']!=result['id'] and other['original']!=result['original']
    assert Path(other['original']).stem.startswith('2026-08-14--interim--H1-2026--')
    saved=archive.documents(Store(tmp_path/'db'),'700.HK')
    assert len(saved)==2 and saved[0]['publisher']=='Example Inc.'
    assert saved[0]['original_filename']=='misleading-annual-2026.md'
    assert len(saved[0]['files'][0]['sha256'])==64


def test_pdf_failure_preserves_original_and_retry(tmp_path,monkeypatch):
    source=tmp_path/'random.pdf';source.write_bytes(b'%PDF-1.4 test fixture')
    monkeypatch.setattr(archive,'read_document',lambda p: ('Annual Report 2025\nPublished: 2026-03-19',{'title':'Exact Title'}))
    def fail(src,dest): raise ValueError('converter unavailable')
    monkeypatch.setattr(archive,'convert_pdf',fail)
    store=Store(tmp_path/'db')
    first=archive.import_document(store,'CRWV.US',source,root=tmp_path/'Research',interactive=False)
    assert Path(first['original']).read_bytes()==source.read_bytes()
    assert first['conversion_status']=='failed' and first['markdown'] is None
    def succeed(src,dest): dest.write_text('# Annual Report 2025');return 'test converter'
    monkeypatch.setattr(archive,'convert_pdf',succeed)
    second=archive.import_document(store,'CRWV.US',source,root=tmp_path/'Research',interactive=False)
    assert second['id']==first['id'] and second['original']==first['original']
    assert Path(second['markdown']).stem==Path(second['original']).stem
    assert second['conversion_status']=='converted'
    assert len(archive.documents(store,'CRWV.US'))==1


async def test_archive_keyboard_expansion_empty_and_narrow(tmp_path):
    from stock.archive_ui import ArchiveApp
    store=Store(tmp_path/'db')
    for i in range(2):
        p=tmp_path/f'{i}.md';p.write_text(f'# Annual Report {2024+i}')
        archive.import_document(store,'700.HK',p,root=tmp_path/'Research',interactive=False)
    app=ArchiveApp('700.HK',store)
    async with app.run_test(size=(80,24)) as pilot:
        assert app.selected==0
        assert 'Unknown' in str(app.query_one('#doc-0').render())
        await pilot.press('space')
        assert 'Sorted' in str(app.query_one('#doc-0').render())
        await pilot.press('down');assert app.selected==1
        await pilot.press('down');assert app.selected==1
        await pilot.resize_terminal(24,12)
        await pilot.press('up','space','escape')
        assert not app.is_running
    empty=ArchiveApp('CRWV.US',store)
    async with empty.run_test(size=(24,12)) as pilot:
        await pilot.press('down','space','o','m','escape')
        assert not empty.is_running


def test_no_partial_registration_on_source_change(tmp_path,monkeypatch):
    p=tmp_path/'report.md';p.write_text('# Annual Report 2025')
    realhash=archive.filehash
    def changed(path): return 'changed' if Path(path).parent.name=='Archive' else realhash(path)
    monkeypatch.setattr(archive,'filehash',changed)
    store=Store(tmp_path/'db')
    with pytest.raises(ValueError,match='changed'):
        archive.import_document(store,'700.HK',p,root=tmp_path/'Research',interactive=False)
    assert archive.documents(store,'700.HK')==[]
    assert list((tmp_path/'Research'/'700.HK'/'Archive').iterdir())==[]


def test_cli_import_is_independent_of_market(tmp_path,monkeypatch,capsys):
    from stock import cli
    store=Store(tmp_path/'db')
    monkeypatch.setattr(cli,'Store',lambda:store)
    monkeypatch.setattr(archive,'ROOT',tmp_path)
    def forbidden(*args): raise AssertionError('Archive must not start market data')
    monkeypatch.setattr(cli,'Market',forbidden)
    source=tmp_path/'article.md';source.write_text('# Annual Report 2025')
    monkeypatch.setattr('sys.argv',['stock','archive','700.HK',str(source)])
    assert cli.main()==0
    assert capsys.readouterr().out=='Archived  undated--annual--FY2025.md\n'


def test_noninteractive_unknown_import_writes_nothing(tmp_path):
    source=tmp_path/'annual-report-2025.md';source.write_text('Unclassified content')
    store=Store(tmp_path/'db')
    with pytest.raises(ValueError,match='type'):
        archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    assert archive.documents(store,'700.HK')==[]
    assert not (tmp_path/'Research').exists()


def test_local_converter_zip_retains_images_and_basename(tmp_path,monkeypatch):
    import subprocess
    import zipfile
    source=tmp_path/'source.pdf';source.write_bytes(b'pdf')
    destination=tmp_path/'2026-03-19--annual--FY2025.md'
    monkeypatch.setattr(archive.shutil,'which',lambda name: '/local/pdfmd' if name=='pdfmd' else None)
    def run(command,**kwargs):
        with zipfile.ZipFile(command[-1],'w') as zipped:
            zipped.writestr('source/source.md','# Report\n![chart](chart.png)')
            zipped.writestr('source/chart.png',b'image')
        return subprocess.CompletedProcess(command,0,'','')
    monkeypatch.setattr(archive,'run_converter',run)
    assert archive.convert_pdf(source,destination)=='pdfmd / Marker'
    assert '2026-03-19--annual--FY2025.assets/chart.png' in destination.read_text()
    assert (tmp_path/'2026-03-19--annual--FY2025.assets'/'chart.png').read_bytes()==b'image'


def test_converter_failure_uses_available_fallback(tmp_path,monkeypatch):
    import subprocess
    destination=tmp_path/'report.md'
    monkeypatch.setattr(archive.shutil,'which',lambda name:'/local/pdfmd')
    monkeypatch.setattr(archive,'pdf_python',lambda:'/local/python')
    def run(command,**kwargs):
        if command[0]=='/local/pdfmd': return subprocess.CompletedProcess(command,1,'','failed')
        return subprocess.CompletedProcess(command,0,'# Converted report\n','')
    monkeypatch.setattr(archive,'run_converter',run)
    assert archive.convert_pdf(tmp_path/'source.pdf',destination)=='pymupdf4llm'
    assert destination.read_text()=='# Converted report\n'


async def test_viewer_keys_use_associated_files(tmp_path,monkeypatch):
    from stock import archive_ui
    source=tmp_path/'report.md';source.write_text('# Annual Report 2025')
    store=Store(tmp_path/'db');doc=archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    opened=[]
    monkeypatch.setattr(archive_ui,'open_file',lambda path,markdown=False:opened.append((path,markdown)))
    app=archive_ui.ArchiveApp('700.HK',store)
    async with app.run_test() as pilot:
        await pilot.press('o','m')
    assert opened==[(doc['original'],False),(doc['original'],True)]


def test_historical_dates_do_not_override_current_publication():
    info=archive.identify('Annual Report 2025\nPublished: 19 March 2026\nOur previous annual report was published on 20 March 2025.',{})
    assert info['date']=='2026-03-19'
    info=archive.identify('Annual Report 2025\nPublished: 19 March 2026 (financial year ended 31 December 2025)',{})
    assert info['date']=='2026-03-19'


def test_fiscal_period_is_not_inferred_from_calendar_month():
    info=archive.identify('Quarterly Report\nFor the first fiscal quarter ended December 31, 2025',{})
    assert info['period'] is None
    info=archive.identify('Interim Report\nFor the six months ended December 31, 2025',{})
    assert info['period'] is None


def test_cover_type_wins_over_table_of_contents():
    assert archive.identify('Annual Report 2025\nContents\nLetter to Shareholders\nEarnings Call Transcript',{})['type']=='Annual'
    assert archive.identify('Investor Presentation\nAnnual results overview',{})['type']=='Presentation'


def test_document_metadata_can_supply_title_and_publisher():
    info=archive.identify('Revenue and operating metrics',{'title':'Annual Report 2025','publisher':'Example Inc.'})
    assert info['type']=='Annual'
    assert info['publisher']=='Example Inc.'


def test_failed_file_registration_rolls_back_copy_and_document(tmp_path):
    source=tmp_path/'report.md';source.write_text('# Annual Report 2025')
    store=Store(tmp_path/'db');archive.schema(store)
    store.db.execute("CREATE TRIGGER reject_archive_file BEFORE INSERT ON archive_files BEGIN SELECT RAISE(ABORT,'test registration failure'); END")
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    assert archive.documents(store,'700.HK')==[]
    assert list((tmp_path/'Research'/'700.HK'/'Archive').iterdir())==[]


def test_conversion_does_not_block_database_writes(tmp_path,monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    source=tmp_path/'report.pdf';source.write_bytes(b'pdf')
    monkeypatch.setattr(archive,'read_document',lambda path:('Annual Report 2025',{}))
    started=threading.Event();release=threading.Event()
    def convert(source,destination):
        started.set()
        assert release.wait(10)
        destination.write_text('# Report');return 'test'
    monkeypatch.setattr(archive,'convert_pdf',convert)
    store=Store(tmp_path/'db')
    with ThreadPoolExecutor() as pool:
        future=pool.submit(archive.import_document,store,'700.HK',source,root=tmp_path/'Research',interactive=False)
        try:
            assert started.wait(5)
            other=Store(tmp_path/'db')
            other.annotate('700.HK','2026-01-01','unrelated annotation')
        finally: release.set()
        assert future.result()['conversion_status']=='converted'
    assert other.annotations('700.HK')=={'2026-01-01':'unrelated annotation'}


async def test_narrow_view_keeps_identity_and_full_metadata_readable(tmp_path):
    from stock.archive_ui import ArchiveApp
    source=tmp_path/'report.md';source.write_text('# Annual Report 2025')
    store=Store(tmp_path/'db');archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    app=ArchiveApp('700.HK',store)
    async with app.run_test(size=(24,24)) as pilot:
        await pilot.press('space')
        text=str(app.query_one('#doc-0').render())
        assert 'FY2025' in text and 'Annual' in text
        assert all(len(line)<=22 for line in text.splitlines())
        assert 'undated--annual--FY2025.md' in text.replace('\n','').replace(' ','')


def test_converter_process_timeout_and_captured_output():
    import subprocess
    import sys
    result=archive.run_converter([sys.executable,'-c','print("# Markdown")'],timeout=5)
    assert result.returncode==0 and result.stdout=='# Markdown\n'
    with pytest.raises(subprocess.TimeoutExpired):
        archive.run_converter([sys.executable,'-c','import time; time.sleep(5)'],timeout=.05)


def test_identical_imports_concurrently_publish_one_document(tmp_path,monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    source=tmp_path/'report.pdf';source.write_bytes(b'pdf')
    monkeypatch.setattr(archive,'read_document',lambda path:('Annual Report 2025',{}))
    barrier=threading.Barrier(2)
    def convert(source,destination):
        barrier.wait(timeout=5)
        destination.write_text('# Converted report');return 'test'
    monkeypatch.setattr(archive,'convert_pdf',convert)
    archive.schema(Store(tmp_path/'db'))
    def run():
        store=Store(tmp_path/'db')
        try: return archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
        finally: store.db.close()
    with ThreadPoolExecutor() as pool:
        futures=[pool.submit(run) for _ in range(2)]
        results=[future.result(timeout=10) for future in futures]
    assert results[0]['id']==results[1]['id']
    assert all(d['conversion_status']=='converted' for d in results)
    assert len(list((tmp_path/'Research'/'700.HK'/'Archive').iterdir()))==2


def test_source_disappearing_before_copy_leaves_no_empty_file(tmp_path,monkeypatch):
    source=tmp_path/'report.md';source.write_text('# Annual Report 2025')
    read=archive.read_document
    def disappear(path):
        content=read(path)
        path.unlink()
        return content
    monkeypatch.setattr(archive,'read_document',disappear)
    store=Store(tmp_path/'db')
    with pytest.raises(FileNotFoundError):
        archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    assert archive.documents(store,'700.HK')==[]
    assert list((tmp_path/'Research'/'700.HK'/'Archive').iterdir())==[]


def test_markdown_registration_failure_preserves_pdf_only(tmp_path,monkeypatch):
    source=tmp_path/'report.pdf';source.write_bytes(b'pdf')
    monkeypatch.setattr(archive,'read_document',lambda path:('Annual Report 2025',{}))
    def convert(source,destination): destination.write_text('# Report');return 'test'
    monkeypatch.setattr(archive,'convert_pdf',convert)
    store=Store(tmp_path/'db');archive.schema(store)
    store.db.execute("CREATE TRIGGER reject_markdown BEFORE INSERT ON archive_files WHEN NEW.role='markdown' BEGIN SELECT RAISE(ABORT,'test markdown failure'); END")
    doc=archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    assert doc['conversion_status']=='failed'
    assert Path(doc['original']).read_bytes()==b'pdf'
    assert not Path(doc['original']).with_suffix('.md').exists()
    assert len(doc['files'])==1


async def test_long_expansion_can_scroll_with_keyboard(tmp_path):
    from stock.archive_ui import ArchiveApp
    source=tmp_path/'report.md';source.write_text('# Annual Report 2025')
    store=Store(tmp_path/'db');archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    app=ArchiveApp('700.HK',store)
    async with app.run_test(size=(30,18)) as pilot:
        await pilot.press('space','pagedown');await pilot.pause()
        assert app.query_one('#rows').scroll_y>0
        await pilot.press('pageup');await pilot.pause()
        assert app.query_one('#rows').scroll_y==0
