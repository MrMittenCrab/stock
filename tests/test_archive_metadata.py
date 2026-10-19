import io
import json
from pathlib import Path
import pytest
from stock import archive
from stock.core import Store

COVER='''UNITED STATES
SECURITIES AND EXCHANGE COMMISSION
FORM 10-Q
QUARTERLY REPORT PURSUANT TO SECTION 13 OR 15(d)
For the quarterly period ended March 31, 2026
Commission file number 001-42563
CoreWeave, Inc.
(Exact name of registrant as specified in its charter)
'''
META={'title':'0001769628-26-000222','subject':'Form 10-Q filed on 2026-05-08 for the period ending 2026-03-31'}


def test_sec_cover_distinguishes_identifiers():
    info=archive.identify(COVER,META)
    assert info['period']=='Q1-2026'
    assert info['accession']=='0001769628-26-000222'
    assert info['title']=='Form 10-Q'
    assert info['publisher']=='CoreWeave, Inc.'
    assert info['date'] is None  # vendor subject is not an authoritative record


def test_missing_prompts_are_compact_and_user_supplied():
    info=archive.identify(COVER,META)
    output=io.StringIO()
    answers=iter(['1',''])
    archive.clarify(info,True,read=lambda _:next(answers),output=output)
    assert output.getvalue()=='Period?  1 Q1-2026 · 2 Unknown · 3 Enter\nDate?  YYYY-MM-DD · Enter Unknown\n'
    assert info['provenance']['date']['source']=='user-supplied'


def test_edit_renames_assets_and_preserves_identity(tmp_path,monkeypatch):
    source=tmp_path/'source.pdf';source.write_bytes(b'pdf')
    monkeypatch.setattr(archive,'read_document',lambda p:(COVER,META))
    monkeypatch.setattr(archive,'resolve_sec',lambda *a:None)
    def convert(src,dest):
        assets=dest.with_suffix('.assets');assets.mkdir()
        (assets/'chart.png').write_bytes(b'image')
        dest.write_text(f'![x]({assets.name}/chart.png)');return 'fixture'
    monkeypatch.setattr(archive,'convert_pdf',convert)
    store=Store(tmp_path/'db')
    doc=archive.import_document(store,'CRWV.US',source,root=tmp_path/'Research',interactive=False)
    edited=archive.update_metadata(store,doc,{'period':'Q1-2026','date':'2026-05-08','title':'Quarterly results'})
    assert edited['id']==doc['id'] and edited['source_sha256']==doc['source_sha256']
    assert Path(edited['original']).name=='2026-05-08--quarterly--Q1-2026.pdf'
    assert '2026-05-08--quarterly--Q1-2026.assets/chart.png' in Path(edited['markdown']).read_text()
    assert all(Path(f['path']).is_file() and archive.filehash(f['path'])==f['sha256'] for f in edited['files'])
    assert source.read_bytes()==b'pdf'
    assert not Path(doc['original']).exists()
    monkeypatch.setattr(archive,'convert_pdf',lambda *a:pytest.fail('reconversion'))
    again=archive.import_document(store,'CRWV.US',source,root=tmp_path/'Research',interactive=False)
    assert again['title']=='Quarterly results' and again['publication_date']=='2026-05-08'
    assert len(archive.documents(store,'CRWV.US'))==1
    assert store.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'


def test_edit_failure_restores_database_and_files(tmp_path):
    source=tmp_path/'source.md';source.write_text('Annual Report 2025')
    store=Store(tmp_path/'db')
    doc=archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    store.db.execute("CREATE TRIGGER reject_edit BEFORE UPDATE ON archive_documents BEGIN SELECT RAISE(ABORT,'reject'); END")
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError): archive.update_metadata(store,doc,{'date':'2026-04-01'})
    assert archive.documents(store,'700.HK')[0]['original']==doc['original']
    assert Path(doc['original']).read_bytes()==source.read_bytes()
    assert len(list(Path(doc['original']).parent.iterdir()))==1


async def test_inline_editor_defaults_optional_fields_and_cancel(tmp_path):
    from stock.archive_ui import ArchiveApp
    from textual.widgets import Input
    source=tmp_path/'report.md';source.write_text('Annual Report 2025\nPublished: 2026-03-19\nPublisher: Example Inc.')
    store=Store(tmp_path/'db')
    doc=archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    app=ArchiveApp('700.HK',store)
    async with app.run_test() as pilot:
        await pilot.press('e')
        assert app.query_one('#edit-date',Input).value=='2026-03-19'
        app.query_one('#edit-date',Input).value='2026-03-20'
        await pilot.press('enter')
        assert not app.editing
        assert app.docs[0]['publication_date']=='2026-03-20'
        assert app.docs[0]['id']==doc['id']
        await pilot.press('e')
        app.query_one('#edit-title',Input).value='Discarded'
        await pilot.press('escape')
        assert app.is_running and not app.editing
        assert app.docs[0]['title']==doc['title']


def test_ambiguous_periods_offer_numbered_choices():
    info=archive.identify('Earnings Presentation\nQ1 2026 / Q2 2026',{})
    assert info['period'] is None
    assert info['period_choices']==['Q1-2026','Q2-2026']
    output=io.StringIO();answers=iter(['2','',''])
    archive.clarify(info,True,read=lambda _:next(answers),output=output)
    assert info['period']=='Q2-2026'
    assert 'Period?  1 Q1-2026 · 2 Q2-2026 · 3 Unknown · 4 Enter' in output.getvalue()


@pytest.mark.parametrize('form,ending,kind,period',[
    ('10-Q','March 31, 2026','Quarterly','Q1-2026'),
    ('10-K','December 31, 2025','Annual','FY2025'),
])
def test_authoritative_sec_date_and_exact_matching(monkeypatch,form,ending,kind,period):
    text=COVER.replace('10-Q',form).replace('March 31, 2026',ending).replace('quarterly period','fiscal year' if form=='10-K' else 'quarterly period')
    info=archive.identify(text,META)
    end='2026-03-31' if form=='10-Q' else '2025-12-31'
    def fetch(url):
        if 'company_tickers' in url: return {'0':{'ticker':'CRWV','cik_str':1769628}}
        return {'name':'CoreWeave, Inc.','fiscalYearEnd':'1231','filings':{'recent':{'accessionNumber':[META['title']],
            'form':[form],'reportDate':[end],'filingDate':['2026-05-08'],'primaryDocument':['crwv.htm']}}}
    monkeypatch.setattr(archive,'sec_json',fetch)
    archive.resolve_sec('CRWV.US',info,META)
    assert (info['type'],info['period'],info['date'])==(kind,period,'2026-05-08')
    assert info['date_evidence'][0]['source']=='SEC submissions'
    assert info['date_evidence'][0]['primary_document']=='crwv.htm'
    wrong=archive.identify(text.replace(ending,'June 30, 2026'),META)
    archive.resolve_sec('CRWV.US',wrong,META)
    assert wrong['date'] is None
    booklet=archive.identify('Annual Report 2025\nShareholder Letter',META)
    archive.resolve_sec('CRWV.US',booklet,META)
    assert booklet['date'] is None


@pytest.mark.parametrize('text,kind,period',[
    ('2025 年度報告','Annual','FY2025'),
    ('中期業績\n截至2026年6月30日止六個月','Interim','H1-2026'),
    ('Q1 2026 Earnings Presentation','Presentation','Q1-2026'),
    ('Corrected Transcript\n07-May-2026\nQ1 2026 Earnings Call','Transcript','Q1-2026'),
])
def test_standard_hk_and_earnings_covers(text,kind,period):
    info=archive.identify(text,{})
    assert (info['type'],info['period'])==(kind,period)
    assert info['date'] is None


def test_collision_preserves_other_document(tmp_path):
    store=Store(tmp_path/'db')
    source=tmp_path/'report.md';source.write_text('Annual Report 2025')
    first=archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    source.write_text('Annual Report 2025\nPublished: 2026-03-19')
    other=archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    original=Path(other['original']).read_bytes()
    edited=archive.update_metadata(store,first,{'date':'2026-03-19'})
    assert edited['original']!=other['original']
    assert Path(other['original']).read_bytes()==original


def test_manual_unknown_and_complete_duplicate_change_nothing(tmp_path,monkeypatch):
    source=tmp_path/'report.md';source.write_text('Annual Report 2025')
    store=Store(tmp_path/'db')
    doc=archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    doc=archive.update_metadata(store,doc,{'date':None,'publisher':None})
    before=store.db.total_changes
    monkeypatch.setattr(archive,'read_document',lambda *a:pytest.fail('complete duplicate read'))
    again=archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=True)
    assert again==doc and store.db.total_changes==before


def test_transcript_title_is_not_a_referenced_form():
    info=archive.identify('Corrected Transcript\nQ1 2026 Earnings Call\nWe filed our Form 10-Q today.',{})
    assert info['title']=='Corrected Transcript'
    assert info['type']=='Transcript'


def test_earlier_publication_keeps_its_own_provenance(monkeypatch):
    info=archive.identify(COVER+'\nPublished: 2026-05-07',META)
    monkeypatch.setattr(archive,'sec_json',lambda url: {'0':{'ticker':'CRWV','cik_str':1769628}} if 'company_tickers' in url else
        {'name':'CoreWeave, Inc.','filings':{'recent':{'accessionNumber':[META['title']],'form':['10-Q'],
        'reportDate':['2026-03-31'],'filingDate':['2026-05-08'],'primaryDocument':['crwv.htm']}}})
    archive.resolve_sec('CRWV.US',info,META)
    assert info['date']=='2026-05-07'
    assert info['provenance']['date']['source']=='document text'


def test_sec_fiscal_calendar_overrides_calendar_month_guess(monkeypatch):
    info=archive.identify(COVER,META)
    monkeypatch.setattr(archive,'sec_json',lambda url:{'0':{'ticker':'CRWV','cik_str':1769628}} if 'company_tickers' in url else
        {'name':'CoreWeave, Inc.','fiscalYearEnd':'0930','filings':{'recent':{'accessionNumber':[META['title']],
        'form':['10-Q'],'reportDate':['2026-03-31'],'filingDate':['2026-05-08'],'primaryDocument':['crwv.htm']}}})
    archive.resolve_sec('CRWV.US',info,META)
    assert info['period']=='Q2-2026'
    assert info['provenance']['period']['source']=='SEC fiscal calendar'


def test_legacy_schema_and_existing_accession_title_reidentified(tmp_path,monkeypatch):
    source=tmp_path/'source.md';source.write_text(COVER)
    store=Store(tmp_path/'db')
    doc=archive.import_document(store,'CRWV.US',source,root=tmp_path/'Research',interactive=False)
    # Model a row written by the previous version, without field provenance.
    with store.db:
        store.db.execute("UPDATE archive_documents SET title=?,period=NULL,metadata_provenance='{}' WHERE id=?",(META['title'],doc['id']))
    monkeypatch.setattr(archive,'read_document',lambda p:(COVER,META))
    monkeypatch.setattr(archive,'resolve_sec',lambda *a:None)
    answers=iter(['1','2026-05-08'])
    monkeypatch.setattr('builtins.input',lambda _:next(answers))
    updated=archive.import_document(store,'CRWV.US',source,root=tmp_path/'Research',interactive=True)
    assert updated['id']==doc['id']
    assert updated['period']=='Q1-2026' and updated['title']=='Form 10-Q'
    assert updated['publication_date']=='2026-05-08'
    assert updated['sec_accession']==META['title']
    assert json.loads(updated['metadata_provenance'])['date']['source']=='user-supplied'
    assert len(archive.documents(store,'CRWV.US'))==1


def test_correction_keeps_future_foreign_key_references(tmp_path):
    source=tmp_path/'source.md';source.write_text('Annual Report 2025')
    store=Store(tmp_path/'db')
    doc=archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    file_id=store.db.execute('SELECT id FROM archive_files').fetchone()[0]
    store.db.execute('PRAGMA foreign_keys=ON')
    store.db.executescript('''CREATE TABLE passages(id INTEGER PRIMARY KEY,doc INTEGER REFERENCES archive_documents(id),file INTEGER REFERENCES archive_files(id));
        CREATE TABLE notes(passage INTEGER REFERENCES passages(id),body TEXT);''')
    with store.db:
        store.db.execute('INSERT INTO passages VALUES(1,?,?)',(doc['id'],file_id))
        store.db.execute("INSERT INTO notes VALUES(1,'Keep annotation')")
    archive.update_metadata(store,doc,{'period':'FY2024','date':'2025-03-19'})
    assert store.db.execute('SELECT doc,file,body FROM passages JOIN notes ON passage=id').fetchone()==(doc['id'],file_id,'Keep annotation')
    assert store.db.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_mid_bundle_failure_restores_pdf_md_assets(tmp_path,monkeypatch):
    source=tmp_path/'source.pdf';source.write_bytes(b'pdf')
    monkeypatch.setattr(archive,'read_document',lambda p:('Annual Report 2025',{}))
    def convert(src,dest):
        assets=dest.with_suffix('.assets');assets.mkdir()
        (assets/'chart.png').write_bytes(b'image')
        dest.write_text(f'![x]({assets.name}/chart.png)');return 'fixture'
    monkeypatch.setattr(archive,'convert_pdf',convert)
    store=Store(tmp_path/'db')
    doc=archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    old={Path(f['path']):Path(f['path']).read_bytes() for f in doc['files']}
    with store.db:
        store.db.execute("CREATE TRIGGER reject_asset_edit BEFORE UPDATE ON archive_files WHEN OLD.role='asset' BEGIN SELECT RAISE(ABORT,'reject asset'); END")
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError): archive.update_metadata(store,doc,{'date':'2026-03-19'})
    assert archive.documents(store,'700.HK')[0]==doc
    assert all(p.read_bytes()==data for p,data in old.items())
    assert set(p for p in Path(doc['original']).parent.rglob('*') if p.is_file())==set(old)


def test_schema_migration_keeps_existing_rows_and_is_idempotent(tmp_path):
    store=Store(tmp_path/'db');archive.schema(store)
    source=tmp_path/'source.md';source.write_text('Annual Report 2025')
    doc=archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    store.db.execute('ALTER TABLE archive_documents DROP COLUMN metadata_provenance')
    store.db.execute('ALTER TABLE archive_documents DROP COLUMN sec_accession')
    store.db.commit()
    archive.schema(store);archive.schema(store)
    updated=archive.documents(store,'700.HK')[0]
    assert updated['id']==doc['id'] and updated['source_sha256']==doc['source_sha256']
    assert updated['metadata_provenance']=='{}'
    assert updated['original']==doc['original']


def test_unknown_title_import_is_supported(tmp_path,monkeypatch):
    source=tmp_path/'source.md';source.write_text('UNITED STATES\nSECURITIES AND EXCHANGE COMMISSION')
    store=Store(tmp_path/'db')
    monkeypatch.setattr('builtins.input',lambda _: '')
    doc=archive.import_document(store,'CRWV.US',source,root=tmp_path/'Research',interactive=True)
    assert doc['title']=='Unknown' and doc['type']=='Unknown'
    assert doc['period'] is None and doc['publication_date'] is None
    assert Path(doc['original']).name=='undated--unknown--Unknown.md'
    assert json.loads(doc['metadata_provenance'])['title']['source']=='user-supplied'


@pytest.mark.parametrize('heading',['2026 Q1 / 2026 Q2 Earnings Presentation','Q1 2026 / 2026 Q2 Earnings Presentation'])
def test_reverse_and_mixed_period_ambiguity(heading):
    info=archive.identify(heading,{})
    assert info['period'] is None
    assert info['period_choices']==['Q1-2026','Q2-2026']


def test_sec_rejects_conflicting_registrant(monkeypatch):
    info=archive.identify(COVER.replace('CoreWeave, Inc.','Other Company, Inc.'),META)
    monkeypatch.setattr(archive,'sec_json',lambda url:{'0':{'ticker':'CRWV','cik_str':1769628}} if 'company_tickers' in url else
        {'name':'CoreWeave, Inc.','filings':{'recent':{'accessionNumber':[META['title']],'form':['10-Q'],
        'reportDate':['2026-03-31'],'filingDate':['2026-05-08'],'primaryDocument':['crwv.htm']}}})
    archive.resolve_sec('CRWV.US',info,META)
    assert info['date'] is None
    assert info['publisher']=='Other Company, Inc.'


async def test_narrow_editor_fields_fit_and_scroll(tmp_path):
    from stock.archive_ui import ArchiveApp
    from textual.widgets import Input
    source=tmp_path/'report.md';source.write_text('Annual Report 2025')
    store=Store(tmp_path/'db')
    archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    app=ArchiveApp('700.HK',store)
    async with app.run_test(size=(40,16)) as pilot:
        await pilot.press('e');await pilot.pause()
        field=app.query_one('#edit-type',Input)
        assert field.region.right<=field.parent.region.right
        await pilot.press('tab','tab','tab','tab');await pilot.pause()
        assert app.focused.id=='edit-publisher'
        assert app.query_one('#edit-publisher').region.bottom<=app.query_one('#editor').region.bottom
        await pilot.press('escape','escape')


async def test_editor_real_keyboard_edits_only_focused_field(tmp_path):
    from stock.archive_ui import ArchiveApp
    from textual.widgets import Input
    source=tmp_path/'report.md';source.write_text('Annual Report 2025\nPublished: 2026-03-19')
    store=Store(tmp_path/'db')
    archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    app=ArchiveApp('700.HK',store)
    async with app.run_test() as pilot:
        await pilot.press('e','tab','tab')
        assert app.focused.id=='edit-date'
        await pilot.press('home','ctrl+k',*list('2026-03-20'),'enter')
        assert not app.editing, str(app.query_one('#status').render())
        assert app.docs[0]['publication_date']=='2026-03-20'
        assert app.docs[0]['type']=='Annual'


@pytest.mark.parametrize('text,period',[
    ('First Quarter 2026 Earnings Presentation','Q1-2026'),
    ('Third Quarter 2025 Earnings Call Transcript','Q3-2025'),
    ('2026 FY Annual Report','FY2026'),
])
def test_written_reporting_periods(text,period):
    info=archive.identify(text,{})
    assert info['period']==period
    assert info['provenance']['period']['source']=='document text'
