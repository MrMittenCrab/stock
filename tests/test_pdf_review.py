"""Review conversion must never publish or overwrite archived evidence."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import tempfile

import pytest

from stock import pdf_review


def test_page_selection_is_one_based_and_validated():
    assert pdf_review.page_range('4,5,6,14,15') == '3,4,5,13,14'
    for value in ('0', '-1', '4,,5', 'x'):
        with pytest.raises(ValueError): pdf_review.page_range(value)


def test_existing_output_and_archive_destinations_are_refused(tmp_path):
    source=tmp_path/'Archive'/'original.pdf';source.parent.mkdir();source.write_bytes(b'pdf')
    with pytest.raises(ValueError): pdf_review.validate_paths(source,source.parent/'review')
    output=tmp_path/'review';output.mkdir()
    with pytest.raises(ValueError): pdf_review.validate_paths(source,output)
    assert source.read_bytes()==b'pdf'


def test_guard_blocks_external_connect_and_connect_ex():
    result=subprocess.run([sys.executable,'-c', '''
from stock import marker_review_worker as worker
import socket
worker.install_network_guard()
for method in ('connect','connect_ex'):
    with socket.socket() as sock:
        try: getattr(sock,method)(('192.0.2.1',443))
        except RuntimeError: pass
        else: raise AssertionError(method)
'''],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_worker_config_disables_enhancements():
    config=pdf_review.marker_config('current',None)
    assert config['use_llm'] is False and config['force_ocr'] is False
    assert config['paginate_output'] is True
    assert config['mode']=='fast'
    assert pdf_review.marker_config('high-fidelity','4,5')['force_ocr'] is True
    assert pdf_review.marker_config('high-fidelity','4,5')['page_range']==[3,4]


def test_watchdog_stops_only_its_own_conversion(tmp_path):
    unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
    child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True)
    try:
        result=pdf_review.monitor(child,seconds=.2,rss_mib=1024)
        assert result['limit']=='time limit'
        assert child.poll() is not None
        assert unrelated.poll() is None
    finally:
        unrelated.terminate();unrelated.wait()
        if child.poll() is None: child.kill();child.wait()


def test_failed_conversion_retains_inactive_manifest():
    with tempfile.TemporaryDirectory(prefix='stock-review-test-') as directory:
        _check_failed_manifest(Path(directory))


def _check_failed_manifest(tmp_path):
    source=tmp_path/'input'/'input.pdf';source.parent.mkdir();source.write_bytes(b'pdf')
    fake=tmp_path/'fake-python'
    fake.write_text('#!/bin/sh\nexit 7\n');fake.chmod(0o755)
    output=tmp_path/'staged'
    result=pdf_review.convert(source,output,python=fake,seconds=2)
    manifest=json.loads((output/'review.json').read_text())
    assert result['returncode']==7
    assert manifest['active_archive'] is False
    assert manifest['source_sha256']==pdf_review.sha256(source)
    assert source.read_bytes()==b'pdf'


def test_success_records_exact_output_and_preserves_interpreter_symlink():
    with tempfile.TemporaryDirectory(prefix='stock-review-test-') as directory:
        root=Path(directory);source=root/'input'/'source.pdf';source.parent.mkdir();source.write_bytes(b'original')
        fake=root/'interpreter'
        fake.write_text('''#!/usr/bin/env python3
import json,sys
from pathlib import Path
out=Path(sys.argv[-1])
(out/'converted.md').write_text('{3}---\\nreview only')
(out/'versions.json').write_text(json.dumps({'marker-pdf':'test'}))
''');fake.chmod(0o755)
        link=root/'venv-python';link.symlink_to(fake)
        result=pdf_review.convert(source,root/'output',python=link,pages='4',seconds=2)
        assert result['returncode']==0
        assert result['output']==str((root/'output').resolve())
        assert result['command'][0]==str(link)
        assert result['pdf_pages']==[4]
        assert result['versions']=={'marker-pdf':'test'}
        assert result['output_files']['converted.md']==pdf_review.sha256(root/'output'/'converted.md')
        assert result['configuration']['mode']=='balanced'
        assert source.read_bytes()==b'original'


def test_external_dns_is_blocked_before_resolution():
    result=subprocess.run([sys.executable,'-c', '''
from stock.marker_review_worker import install_network_guard
import socket
install_network_guard()
try: socket.getaddrinfo('example.invalid',443)
except RuntimeError: pass
else: raise AssertionError('external DNS was permitted')
assert socket.getaddrinfo('127.0.0.1',443)
'''],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
