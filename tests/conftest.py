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
