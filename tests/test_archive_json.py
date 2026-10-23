import json
from pathlib import Path
import pytest
from stock import archive
from stock.core import Store


@pytest.fixture(autouse=True)
def offline_by_default(monkeypatch):
    def unavailable(url): raise OSError('offline test')
    monkeypatch.setattr(archive,'sec_json',unavailable)


def setup_archive(tmp_path):
    store=Store(tmp_path/'db')
    source=tmp_path/'report.md'
    source.write_text('CoreWeave\nCorrected Transcript\nFactSet CallStreet\nQ1 2026 Earnings Call')
    doc=archive.import_document(store,'CRWV.US',source,root=tmp_path/'Research',interactive=False)
    payload={'schema_version':'stock.archive.metadata.v1','ticker':'CRWV.US','issuer':'CoreWeave, Inc.',
        'documents':[{'match':{'original_filename':'report.md','content_indicators':['Corrected Transcript','FactSet CallStreet','Q1 2026 Earnings Call']},
        'metadata':{'type':'Transcript','period':'Q1-2026','title':'Exact title','publisher':'FactSet CallStreet, LLC',
        'publication_date':None,'event_date':'2026-05-07','document_date':'2026-05-07'}}]}
    path=tmp_path/'metadata.json';path.write_text(json.dumps(payload))
    return store,doc,payload,path


def test_json_enrichment_idempotent_distinct_dates(tmp_path):
    store,doc,payload,path=setup_archive(tmp_path)
    assert archive.import_metadata(store,'CRWV.US',path,interactive=False)==1
    updated=archive.documents(store,'CRWV.US')[0]
    assert updated['id']==doc['id'] and updated['source_sha256']==doc['source_sha256']
    assert updated['publication_date'] is None
    assert json.loads(updated['structured_metadata'])['event_date']=='2026-05-07'
    assert updated['title']=='Exact title'
    before=store.db.total_changes
    assert archive.import_metadata(store,'CRWV.US',path,interactive=False)==0
    assert store.db.total_changes==before


def test_json_manual_conflict_requires_choice(tmp_path):
    store,doc,payload,path=setup_archive(tmp_path)
    archive.update_metadata(store,doc,{'title':'Manual title','publisher':None})
    with pytest.raises(ValueError,match='conflict'):
        archive.import_metadata(store,'CRWV.US',path,interactive=False)
    assert archive.documents(store,'CRWV.US')[0]['title']=='Manual title'


@pytest.mark.parametrize('alter',[
    lambda p:p.update(schema_version='v2'),
    lambda p:p['documents'][0]['metadata'].update(event_date='2026-02-30'),
    lambda p:p['documents'][0]['match'].pop('content_indicators'),
    lambda p:p['documents'][0]['match'].update(sha256='0'*64),
    lambda p:p['documents'][0]['metadata'].update(type='Annual'),
    lambda p:p['documents'].append(p['documents'][0]),
])
def test_json_rejects_invalid_contradictory_or_duplicate_records(tmp_path,alter):
    store,doc,payload,path=setup_archive(tmp_path)
    alter(payload);path.write_text(json.dumps(payload))
    with pytest.raises(ValueError): archive.import_metadata(store,'CRWV.US',path,interactive=False)
    assert archive.documents(store,'CRWV.US')[0]==doc


def test_filing_basis_never_becomes_publication_date(tmp_path):
    store,doc,payload,path=setup_archive(tmp_path)
    payload['documents'][0]['metadata'].update(publication_date='2026-05-08',publication_date_basis='SEC filing date (filed as of)')
    path.write_text(json.dumps(payload))
    archive.import_metadata(store,'CRWV.US',path,interactive=False)
    updated=archive.documents(store,'CRWV.US')[0]
    assert updated['publication_date'] is None
    assert json.loads(updated['structured_metadata'])['filing_date']=='2026-05-08'


def test_automatic_document_dates_and_publisher(tmp_path):
    store=Store(tmp_path/'db')
    source=tmp_path/'call.md'
    source.write_text('Corrected Transcript\nCoreWeave, Inc.\nQ1 2026 Earnings Call\n07-May-2026\nCopyright FactSet CallStreet, LLC')
    doc=archive.import_document(store,'CRWV.US',source,root=tmp_path/'Research',interactive=False)
    meta=json.loads(doc['structured_metadata'])
    assert meta['event_date']=='2026-05-07'
    assert meta['document_date']=='2026-05-07'
    assert doc['publication_date'] is None
    assert doc['publisher']=='FactSet CallStreet, LLC'


def test_json_values_survive_duplicate_import(tmp_path):
    store,doc,payload,path=setup_archive(tmp_path)
    archive.import_metadata(store,'CRWV.US',path,interactive=False)
    before=archive.documents(store,'CRWV.US')[0]
    again=archive.import_document(store,'CRWV.US',tmp_path/'report.md',root=tmp_path/'Research',interactive=False)
    assert again==before


def test_batch_sql_failure_rolls_back_every_document(tmp_path):
    store,doc,payload,path=setup_archive(tmp_path)
    source=tmp_path/'second.md';source.write_text('CoreWeave\nAnnual Report 2025')
    second=archive.import_document(store,'CRWV.US',source,root=tmp_path/'Research',interactive=False)
    payload['documents'].append({'match':{'sha256':second['source_sha256']},'metadata':{'title':'Second title','publication_date':'2026-04-22'}})
    payload['documents'][0]['metadata']['publication_date']='2026-05-08'
    path.write_text(json.dumps(payload));before=archive.documents(store,'CRWV.US')
    store.db.execute(f"CREATE TRIGGER reject_second BEFORE UPDATE ON archive_documents WHEN OLD.id={second['id']} BEGIN SELECT RAISE(ABORT,'reject'); END")
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError): archive.import_metadata(store,'CRWV.US',path,interactive=False)
    assert archive.documents(store,'CRWV.US')==before
    assert all(Path(d['original']).is_file() for d in before)
    assert len(list(Path(doc['original']).parent.glob('*.md')))==2


def test_sec_resolution_retains_filing_not_publication(monkeypatch):
    text='FORM 10-Q\nFor the quarterly period ended March 31, 2026\nCoreWeave, Inc.\n(Exact name of registrant)'
    info=archive.identify(text,{'title':'0001769628-26-000222'})
    monkeypatch.setattr(archive,'sec_json',lambda u:{'0':{'ticker':'CRWV','cik_str':1769628}} if 'company_tickers' in u else
        {'name':'CoreWeave, Inc.','filings':{'recent':{'accessionNumber':['0001769628-26-000222'],'form':['10-Q'],
        'reportDate':['2026-03-31'],'filingDate':['2026-05-08'],'primaryDocument':['crwv.htm']}}})
    archive.resolve_sec('CRWV.US',info,{})
    assert info['date'] is None
    assert info['structured']['filing_date']=='2026-05-08'


@pytest.mark.parametrize('failure',[OSError('offline'),ValueError('blocked'),KeyError('missing')])
def test_sec_unavailable_leaves_unknown(monkeypatch,failure):
    info=archive.identify('FORM 10-Q\nFor the quarterly period ended March 31, 2026',{'title':'0001769628-26-000222'})
    def fail(url): raise failure
    monkeypatch.setattr(archive,'sec_json',fail)
    archive.resolve_sec('CRWV.US',info,{})
    assert info['date'] is None and 'filing_date' not in info['structured']


def test_ambiguous_identical_names_rejected(tmp_path):
    store,doc,payload,path=setup_archive(tmp_path)
    source=tmp_path/'report.md';source.write_text(source.read_text()+'\nAdditional text')
    archive.import_document(store,'CRWV.US',source,root=tmp_path/'Research',interactive=False)
    with pytest.raises(ValueError,match='Ambiguous'): archive.import_metadata(store,'CRWV.US',path,interactive=False)


def test_embedded_source_page_requires_exact_pdf(tmp_path,monkeypatch):
    source=tmp_path/'report.pdf';source.write_bytes(b'%PDF-exact')
    info=archive.identify('Investor Presentation',{})
    page=b'<meta name="citation_pdf_url" content="/report.pdf"><meta name="citation_publisher" content="Issuer Inc."><meta name="citation_publication_date" content="2026-05-07">'
    monkeypatch.setattr(archive,'fetch_source',lambda url:(page,url,'text/html') if url.endswith('/page') else (b'%PDF-wrong',url,'application/pdf'))
    archive.resolve_linked_source(info,{'source_url':'https://issuer.example/page'},source)
    assert info['date'] is None and info['publisher'] is None
    monkeypatch.setattr(archive,'fetch_source',lambda url:(page,url,'text/html') if url.endswith('/page') else (source.read_bytes(),url,'application/pdf'))
    archive.resolve_linked_source(info,{'source_url':'https://issuer.example/page'},source)
    assert info['date']=='2026-05-07' and info['publisher']=='Issuer Inc.'
    assert info['provenance']['date']['identity_sha256']==archive.filehash(source)


def test_automatic_issuer_lookup_verifies_document_content(monkeypatch):
    info=archive.identify('CoreWeave\nAnnual Report 2025',{})
    monkeypatch.setattr(archive,'sec_json',lambda u:{'0':{'ticker':'CRWV','cik_str':1769628}} if 'company_tickers' in u else {'name':'CoreWeave, Inc.','filings':{'recent':{}}})
    archive.resolve_issuer('CRWV.US',info,'CoreWeave\nAnnual Report 2025')
    assert info['publisher']=='CoreWeave, Inc.'
    assert info['date'] is None
    wrong=archive.identify('Other Company\nAnnual Report 2025',{})
    archive.resolve_issuer('CRWV.US',wrong,'Other Company\nAnnual Report 2025')
    assert wrong['publisher'] is None


def test_content_only_identity_can_match(tmp_path):
    store,doc,payload,path=setup_archive(tmp_path)
    del payload['documents'][0]['match']['original_filename']
    path.write_text(json.dumps(payload))
    assert archive.import_metadata(store,'CRWV.US',path,interactive=False)==1


def test_hash_disambiguates_reused_original_filename(tmp_path):
    store,doc,payload,path=setup_archive(tmp_path)
    source=tmp_path/'report.md';source.write_text('CoreWeave\nAnnual Report 2025')
    other=archive.import_document(store,'CRWV.US',source,root=tmp_path/'Research',interactive=False)
    payload['documents'][0]['match']['sha256']=doc['source_sha256']
    path.write_text(json.dumps(payload))
    assert archive.import_metadata(store,'CRWV.US',path,interactive=False)==1
    assert next(d for d in archive.documents(store,'CRWV.US') if d['id']==other['id'])==other


def test_contradictory_hash_aliases_rejected(tmp_path):
    store,doc,payload,path=setup_archive(tmp_path)
    payload['documents'][0]['match'].update(sha256=doc['source_sha256'],source_sha256='0'*64)
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='Contradictory'): archive.import_metadata(store,'CRWV.US',path,interactive=False)


def test_json_dates_survive_partial_duplicate_refresh(tmp_path,monkeypatch):
    store,doc,payload,path=setup_archive(tmp_path)
    source=tmp_path/'report.md'
    source.write_text(source.read_text()+'\n07-May-2026')
    # Refresh identity to a document that contains an inferred cover date.
    doc=archive.import_document(store,'CRWV.US',source,root=tmp_path/'Research',interactive=False)
    payload['documents'][0]['match']={'sha256':doc['source_sha256']}
    payload['documents'][0]['metadata']={'event_date':'2026-05-06'}
    path.write_text(json.dumps(payload))
    archive.import_metadata(store,'CRWV.US',path,interactive=False)
    # Simulate a previously unresolved title now available from embedded metadata.
    monkeypatch.setattr(archive,'read_document',lambda p:(source.read_text(),{'title':'Newly identified title'}))
    again=archive.import_document(store,'CRWV.US',source,root=tmp_path/'Research',interactive=False)
    assert again['title']=='Newly identified title'
    assert json.loads(again['structured_metadata'])['event_date']=='2026-05-06'


@pytest.mark.parametrize('bad',[7,[],{},True])
def test_malformed_hash_alias_is_validation_error(tmp_path,bad):
    store,doc,payload,path=setup_archive(tmp_path)
    payload['documents'][0]['match'].update(sha256=doc['source_sha256'],source_sha256=bad)
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError): archive.import_metadata(store,'CRWV.US',path,interactive=False)


def test_export_preserves_publication_provenance(tmp_path):
    store,doc,payload,path=setup_archive(tmp_path)
    doc=archive.update_metadata(store,doc,{'date':'2026-05-08'})
    exported=archive.export_metadata(store,'CRWV.US')
    meta=exported['documents'][0]['metadata']
    assert meta['publication_date']=='2026-05-08'
    assert meta['publication_date_basis']=='user-supplied'


def test_presentation_cover_date_excludes_disclaimer_reporting_end():
    info=archive.identify('Earnings Presentation\nQ1 2026\nMay 7, 2026\nForward-Looking Statements\nFor the quarter ended March 31, 2026',{})
    assert info['structured']['document_date']=='2026-05-07'
    assert info['date'] is None


@pytest.mark.parametrize('raw',['{','{"schema_version":"stock.archive.metadata.v1","schema_version":"stock.archive.metadata.v1"}'])
def test_malformed_or_duplicate_json_keys(tmp_path,raw):
    store,doc,payload,path=setup_archive(tmp_path)
    path.write_text(raw)
    with pytest.raises(ValueError): archive.import_metadata(store,'CRWV.US',path,interactive=False)
    assert archive.documents(store,'CRWV.US')[0]==doc


def test_mid_publication_disk_failure_restores_bundle(tmp_path,monkeypatch,fake_pdf_quality):
    store=Store(tmp_path/'db');source=tmp_path/'source.pdf';source.write_bytes(b'pdf')
    monkeypatch.setattr(archive,'read_document',lambda p:('Annual Report 2025',{}))
    def convert(src,dest): dest.write_text('# Original conversion');return 'fixture'
    monkeypatch.setattr(archive,'convert_pdf',convert)
    doc=archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    before={f['path']:Path(f['path']).read_bytes() for f in doc['files']}
    real_open=Path.open
    def fail(self,mode='r',*args,**kwargs):
        if mode=='xb' and self.name=='2026-04-22--annual--FY2025.md': raise OSError('disk full')
        return real_open(self,mode,*args,**kwargs)
    monkeypatch.setattr(Path,'open',fail)
    with pytest.raises(OSError,match='disk full'): archive.update_metadata(store,doc,{'date':'2026-04-22'})
    assert archive.documents(store,'700.HK')[0]==doc
    assert {str(p):p.read_bytes() for p in Path(doc['original']).parent.iterdir()}==before


def test_keep_manual_conflict_is_idempotent_and_preserves_evidence(tmp_path,monkeypatch):
    store,doc,payload,path=setup_archive(tmp_path)
    doc=archive.update_metadata(store,doc,{'date':'2026-05-09','title':'Manual title'})
    payload['documents'][0]['metadata'].update(publication_date='2026-05-08',publication_date_basis='Different evidence')
    path.write_text(json.dumps(payload));prompts=[]
    monkeypatch.setattr('builtins.input',lambda prompt:(prompts.append(prompt) or 'k'))
    archive.import_metadata(store,'CRWV.US',path,interactive=True)
    updated=archive.documents(store,'CRWV.US')[0]
    assert updated['title']=='Manual title' and updated['publication_date']=='2026-05-09'
    assert 'Different evidence' not in updated['structured_metadata']
    assert len(prompts)==2
    before=store.db.total_changes
    assert archive.import_metadata(store,'CRWV.US',path,interactive=False)==0
    assert store.db.total_changes==before
