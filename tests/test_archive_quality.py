import json
from pathlib import Path
import pytest
from stock import archive, archive_quality as quality
from stock.core import Store


def page(text='CoreWeave builds AI infrastructure.',number=1,**kw):
    return dict(page=number,width=1000,height=800,blocks=[dict(id=f'p{number}b0',bbox=[10,20,500,100],text=text)],images=[],drawings=0,**kw)


def test_region_loss_not_hidden_by_high_recall():
    pages=[page('CoreWeave builds AI infrastructure. '*500+'Cognition Cursor SUNK CKS W&B Models')]
    result=quality.assess(pages,'CoreWeave builds AI infrastructure. '*500)[0]
    assert result['word_recall']>.99
    assert 'cursor' in result['missing_regions'][0]['missing_words']


def test_formatting_and_footnote_normalization():
    assert not quality.assess([page('Revenue Backlog1\nAI-native growth')],'## **Revenue Backlog**¹\nAI-native growth')[0]['missing_regions']
    assert not quality.assess([page('AI is important.')],'**AI** is important.')[0]['missing_regions']
    assert quality.assess([page('AI is important.')],'Al is important.')[0]['missing_regions']


def test_native_recovery_exact_provenance_and_no_ocr(tmp_path,monkeypatch):
    original=tmp_path/'original.pdf';original.write_bytes(b'original')
    md=tmp_path/'source.md';md.write_text('CoreWeave builds AI infrastructure.')
    exact='Key Product: W&B Models\nSlurm on Kubernetes (SUNK)\n'
    monkeypatch.setattr(quality,'native_pages',lambda _: [page(exact)])
    def forbidden(*a):raise AssertionError('clean native text does not need OCR')
    result=quality.prepare(original,md,'fixture',ocr=forbidden)
    r=result['regions'][0]
    assert md.read_text()[r['start']:r['end']]==exact.rstrip('\n')
    assert r['kind']=='native_pdf_region' and r['page']==1 and r['bbox']==[10,20,500,100]
    assert result['quality_status']=='prepared'


def test_bounded_ocr_and_visual_evidence(tmp_path,monkeypatch):
    original=tmp_path/'original.pdf';original.write_bytes(b'original')
    md=tmp_path/'source.md';md.write_text('')
    pages=[dict(page=i,width=100,height=100,blocks=[],images=[[0,0,100,100]],drawings=0) for i in range(1,6)]
    monkeypatch.setattr(quality,'native_pages',lambda _:pages)
    calls=[]
    def ocr(src,numbers,out):
        calls.extend(numbers)
        return dict(returncode=0,markdown='CoreWeave explains its AI strategy and operating constraints.')
    result=quality.prepare(original,md,'fixture',ocr=ocr)
    assert calls==[1,2,3]
    assert result['quality_status']=='needs_repair'
    assert len(result['attempts'])==3
    assert all(r['kind']=='local_ocr_region' for r in result['regions'])


def test_repair_candidate_keeps_sorted_files_and_citations(tmp_path,monkeypatch):
    from stock import sources
    source=tmp_path/'source.md';source.write_text('# Annual Report 2025\n\nCoreWeave builds AI infrastructure.')
    store=Store(tmp_path/'db')
    doc=archive.import_document(store,'CRWV.US',source,root=tmp_path/'Research',interactive=False)
    original=Path(doc['original']).with_suffix('.pdf');original.write_bytes(b'original')
    with store.db:
        store.db.execute("UPDATE archive_files SET role='markdown' WHERE document_id=?",(doc['id'],))
        store.db.execute('INSERT INTO archive_files(document_id,role,path,sha256) VALUES(?,?,?,?)',(doc['id'],'original',str(original),archive.filehash(original)))
        store.db.execute("UPDATE archive_documents SET source_sha256=?,conversion_status='converted',sorted_at=1 WHERE id=?",(archive.filehash(original),doc['id']))
    sources.schema(store)
    with store.db:store.db.execute('INSERT INTO source_sorts VALUES(?,?,?,5)',(doc['id'],1,archive.filehash(original)))
    monkeypatch.setattr(quality,'native_pages',lambda _: [page('Cognition and Cursor are named customers.')])
    before=Path(doc['markdown']).read_bytes()
    result=archive.repair_document(store,'CRWV.US',doc['id'])
    fresh=archive.documents(store,'CRWV.US')[0]
    assert not result['active'] and fresh['markdown']==doc['markdown']
    assert Path(doc['markdown']).read_bytes()==before
    manifest=json.loads(Path(result['manifest']).read_text())
    candidate={**fresh,'markdown':str(Path(result['manifest']).with_suffix('.md')),'evidence':result['manifest']}
    # The manifest is source.evidence.json; Markdown is source.md.
    candidate['markdown']=str(Path(result['manifest']).parent/'source.md')
    from stock.knowledge import prepare_atoms
    text=Path(candidate['markdown']).read_text()
    atoms=prepare_atoms(text,candidate,manifest['markdown_sha256'])
    recovered=[a for a in atoms if a.get('source_kind')=='native_pdf_region']
    assert recovered and recovered[0]['page']==1
    assert recovered[0]['pdf_region']['bbox']==[10,20,500,100]
    from stock.editorial import resolve_selection, inspection
    selection=dict(ids=[recovered[0]['id']],topics=['Market'],category='Management',speaker=None,
                   representation='verbatim',text=None,ambiguities=[])
    passage=resolve_selection(selection,atoms,text,candidate,manifest['markdown_sha256'])
    assert passage['location']['kind']=='original PDF region'
    assert passage['location']['references'][0]['evidence_type']=='native_pdf_region'
    assert 'PDF region [10, 20, 500, 100]' in inspection(passage)
    monkeypatch.setattr(quality,'native_pages',lambda _:pytest.fail('equivalent repair repeated'))
    assert archive.repair_document(store,'CRWV.US',doc['id'])['reused']


def test_page_anchors_do_not_hide_name_loss_on_another_page():
    p1=page('CoreWeave customer wins have continued across AI labs. Cognition and Cursor.',1)
    p2=page('CoreWeave product development has continued across AI infrastructure. Cognition and Cursor.',2)
    converted='CoreWeave customer wins have continued across AI labs.\nCoreWeave product development has continued across AI infrastructure. Cognition and Cursor.'
    first=quality.assess([p1,p2],converted)[0]
    assert first['missing_regions']


def test_prepared_sort_never_converts(tmp_path,monkeypatch):
    md=tmp_path/'source.md';md.write_text('CoreWeave strategy')
    original=tmp_path/'source.pdf';original.write_bytes(b'original')
    doc=dict(id=1,ticker='CRWV.US',original=str(original),markdown=str(md),conversion_status='converted',quality_status='prepared_with_visual_limitations')
    monkeypatch.setattr(archive,'_convert_registered',lambda *a:pytest.fail('redundant conversion'))
    assert archive.prepare_for_sort(None,doc,lambda _:None)==doc


def test_clean_transcript_avoids_layout_ocr(tmp_path,monkeypatch):
    original=tmp_path/'original.pdf';original.write_bytes(b'original')
    md=tmp_path/'source.md';md.write_text('AI infrastructure is strategically important.')
    p=page('AI infrastructure is strategically important. We expect 850MW+ and 3.1GW+ power.')
    monkeypatch.setattr(quality,'native_pages',lambda _:[p])
    def forbidden(*a):pytest.fail('numeric transcript prose must not force OCR')
    result=quality.prepare(original,md,'fixture',ocr=forbidden,document_type='Transcript')
    assert not result['attempts']
    assert 'AI infrastructure' in md.read_text() and 'Al infrastructure' not in md.read_text()


def test_quality_failure_cannot_register_nonempty_markdown(tmp_path,monkeypatch):
    original=tmp_path/'source.pdf';original.write_bytes(b'original')
    monkeypatch.setattr(archive,'read_document',lambda _:('Annual Report 2025',{}))
    def convert(src,dest):dest.write_text('Nonempty conversion');return 'fixture'
    monkeypatch.setattr(archive,'convert_pdf',convert)
    monkeypatch.setattr(quality,'native_pages',lambda _:(_ for _ in ()).throw(ValueError('quality check failed')))
    store=Store(tmp_path/'db')
    doc=archive.import_document(store,'700.HK',original,root=tmp_path/'Research',interactive=False)
    assert doc['conversion_status']=='failed' and not doc['markdown']
    assert Path(doc['original']).read_bytes()==b'original'
    assert not store.db.execute('SELECT 1 FROM archive_evidence_versions').fetchone()


def test_sort_requests_archive_once_for_invalid_manifest(tmp_path,monkeypatch):
    original=tmp_path/'source.pdf';original.write_bytes(b'original')
    md=tmp_path/'source.md';md.write_text('CoreWeave strategy')
    manifest=tmp_path/'source.evidence.json';manifest.write_text('{}')
    doc=dict(id=1,ticker='CRWV.US',original=str(original),source_sha256=archive.filehash(original),
             markdown=str(md),evidence=str(manifest),conversion_status='converted',quality_status='prepared')
    calls=[]
    def repair(*args):
        calls.append(args)
        manifest.write_text(json.dumps(dict(schema='stock.archive.evidence',version=1,
            original_sha256=archive.filehash(original),markdown_sha256=archive.filehash(md),regions=[],pages=[])))
    monkeypatch.setattr(archive,'repair_document',repair)
    monkeypatch.setattr(archive,'documents',lambda *args:[doc])
    monkeypatch.setattr(archive,'_convert_registered',lambda *a:pytest.fail('duplicate preparation'))
    assert archive.prepare_for_sort(None,doc,lambda _:None)==doc
    assert len(calls)==1
