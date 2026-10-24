import json
import pytest


@pytest.fixture
def fake_pdf_quality(monkeypatch):
    """Isolate legacy registration tests whose converters use literal fake PDFs.

    Real assessment, recovery, OCR bounds and provenance have separate tests.
    """
    def prepare(original,markdown,converter,**kwargs):
        from stock.archive import filehash
        data=dict(schema='stock.archive.evidence',version=1,original_sha256=filehash(original),
                  markdown_sha256=filehash(markdown),converter=converter,quality_status='prepared',
                  pages=[],regions=[],attempts=[],elapsed_seconds=0)
        markdown.with_suffix('.evidence.json').write_text(json.dumps(data))
        return data
    monkeypatch.setattr('stock.archive_quality.prepare',prepare)


@pytest.fixture(autouse=True)
def offline_semantics(monkeypatch):
    """Deterministic semantic dependencies for workflow tests, not accuracy evidence."""
    import numpy as np
    from stock import relationships,semantic_map
    class Encoder:
        def embed(self,texts,batch_size=None):
            for _ in texts:
                v=np.zeros(384,dtype=np.float32);v[0]=1;yield v
    def infer(pairs):
        return [dict(entailment=.995,contradiction=.002,neutral=.003) for _ in pairs]
    monkeypatch.setattr(semantic_map,'_model',lambda:Encoder())
    monkeypatch.setattr(relationships,'backend',lambda:infer)
    return infer
