"""Opt-in fresh authenticated CoreWeave extraction; only disposable DBs are mutated.
PYTHONPATH=. .venv/bin/python tests/verify_sort_real.py
"""
import json
import tempfile
import sys
from contextlib import nullcontext
from pathlib import Path
from stock.core import ROOT, Store
from stock.archive import documents, filehash
from stock.sort import Cursor, units, validate, sort_document
from stock import sources


def main():
    live=Store()
    before=live.db.iterdump()
    snapshot='\n'.join(before)
    docs=documents(live,'CRWV.US')
    cursor=Cursor()
    with nullcontext(tempfile.mkdtemp(prefix='verify-sort-',dir=ROOT/'.data')) as directory:
        print('Verification DB copy: '+str(directory),flush=True)
        trial=Store(Path(directory)/'stock.sqlite3')
        live.db.backup(trial.db)
        sources.schema(trial)
        frozen={table:trial.db.execute(f'SELECT * FROM {table} ORDER BY 1,2').fetchall()
                for table in ('source_passages','source_topics','source_overrides','source_sorts')}
        evidence=[]
        for doc in [next(d for d in docs if d['type']==kind and not sources.completed(trial,d['id']))
                    for kind in ('Transcript','Quarterly','Annual')]:
            text=Path(doc['markdown']).read_text(encoding='utf-8-sig')
            work=list(units(text))
            # Later narrative sections reproduce the original PDF-anchor failures.
            if doc['type']=='Quarterly':
                start=text.index("## **Item 2. Management's Discussion")
                unit=next(units(text[start:]));unit['start']+=start
            else:
                unit=work[min(2,len(work)-1)]
            edge=unit['text'].rfind('\n\n',0,6500)
            if edge>0: unit={**unit,'text':unit['text'][:edge]}
            context='Document title: '+doc['title']+'\nPublisher: '+(doc['publisher'] or 'Unknown')+'\nFront matter (untrusted):\n'+text[:6500]
            artifact=ROOT/'.data'/f'verify-sort-repair-{doc["id"]}.json'
            cached=json.loads(artifact.read_text()) if '--resume' in sys.argv and artifact.exists() else None
            if cached and cached['unit']==unit and cached['context']==context:
                print(f"Revalidating fresh authenticated response: {doc['id']} · {doc['type']}",flush=True)
                candidates=cached['candidates']
            else:
                print(f"Fresh authenticated extraction: {doc['id']} · {doc['type']}",flush=True)
                candidates=cursor.extract(unit,context)
                artifact.write_text(json.dumps(dict(unit=unit,context=context,candidates=candidates),ensure_ascii=False,indent=2))
            accepted=[];rejected=[]
            for raw in candidates:
                try: accepted.append(validate(raw,unit,context,doc,None,'archived Markdown',filehash(doc['markdown'])))
                except ValueError as exc:
                    print(f'  Targeted retry: {exc}',flush=True)
                    retry=cursor.extract(unit,context+'\nRepair only this candidate using this error: '+str(exc)+'\n'+json.dumps(raw))
                    try:
                        if not retry: raise ValueError(str(exc))
                        accepted.extend(validate(r,unit,context,doc,None,'archived Markdown',filehash(doc['markdown'])) for r in retry)
                    except ValueError as error: rejected.append(str(error))
            assert accepted, 'No verified real passages'
            for p in accepted:
                loc=p['location']
                assert text[loc['start']:loc['end']]==p['text']
                assert loc['sha256']==loc['markdown_sha256']==filehash(doc['markdown'])
                assert loc['page'] is None and loc['verification']=='Exact archived Markdown text'
            evidence.extend(dict(document_id=doc['id'],**p) for p in accepted)
            print(f"  {len(accepted)} verified, {len(rejected)} rejected: {rejected}",flush=True)
        # Actual Archive conversion on a copied real PDF, then full authenticated sort.
        doc=next(d for d in docs if d['id']==13)
        if '--reuse-conversion' not in sys.argv:
            original=Path(directory)/'copied-presentation.pdf'
            original.write_bytes(Path(doc['original']).read_bytes())
            with trial.db:
                trial.db.execute('DELETE FROM archive_files WHERE document_id=? AND role!=?',(doc['id'],'original'))
                trial.db.execute('UPDATE archive_files SET path=? WHERE document_id=? AND role=?',(str(original),doc['id'],'original'))
                trial.db.execute("UPDATE archive_documents SET conversion_status='failed' WHERE id=?",(doc['id'],))
            doc=next(d for d in documents(trial,'CRWV.US') if d['id']==13)
            print('Converting copied real PDF before full authenticated sort',flush=True)
        else:
            print('Reusing archived conversion for full authenticated sort',flush=True)
        print('  Passages:',sort_document(trial,doc,cursor),flush=True)
        assert sources.completed(trial,doc['id'])
        class Forbidden:
            def extract(self,*args): raise AssertionError('Completed document rerun')
        assert sort_document(trial,doc,Forbidden()) is None
        for table,rows in frozen.items():
            assert all(row in trial.db.execute(f'SELECT * FROM {table}').fetchall() for row in rows)
        (ROOT/'.data/verified-sort-repair-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
        trial.db.close()
    assert snapshot=='\n'.join(live.db.iterdump()), 'User database changed'
    live.db.close()
    basis='conversion reuse' if '--reuse-conversion' in sys.argv else 'real PDF conversion'
    print(f'Authenticated extraction, {basis}, anchors, freeze and user-data preservation verified',flush=True)


if __name__=='__main__': main()
