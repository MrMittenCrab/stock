"""Compact model transport; canonical evidence and provenance stay in Stock."""
import json

SOURCE_FIELDS=('id','text','section','turn','speaker','role','speaker_role','context_only','source_kind','page','table','evidence_type')
REFERENCE_FIELDS=('source_id','text','section','turn','page','table','evidence_type')


def source_payload(source):
    payload={k:source[k] for k in SOURCE_FIELDS if source.get(k) is not None}
    if source.get('table'):payload['table']={k:v for k,v in source['table'].items() if k in ('id','row','column','ambiguous')}
    return payload


def reference_payload(ref):
    payload={k:ref[k] for k in REFERENCE_FIELDS if ref.get(k) is not None}
    if ref.get('table'):payload['table']={k:v for k,v in ref['table'].items() if k in ('id','row','column','ambiguous')}
    return payload


def selection_batches(atoms, limit=14000):
    """Budget the source data the model sees, not repeated local provenance."""
    batch=[];size=0
    for atom in atoms:
        cost=len(json.dumps(source_payload(atom),ensure_ascii=False))
        if batch and size+cost>limit:
            yield batch;batch=[];size=0
        batch.append(atom);size+=cost
    if batch:yield batch
