import io
import subprocess
import sys

from stock import archive


def test_prospectus_rejects_generic_metadata():
    info=archive.identify('Table of Contents\nPROSPECTUS\nCoreWeave, Inc.\nThis is our initial public offering of common stock.', {'title':'Table of Contents'})
    assert info['title']=='CoreWeave, Inc. IPO Prospectus'
    assert info['type']=='Filing'
    assert info['date'] is None


def test_sec_registration_title():
    info=archive.identify('UNITED STATES\nSECURITIES AND EXCHANGE COMMISSION\nFORM S-1/A\nCoreWeave, Inc.\n(Exact name of registrant as specified in its charter)', {'title':'Contents'})
    assert info['title']=='CoreWeave, Inc. Form S-1/A'
    assert info['sec_form']=='S-1/A'


def test_long_running_converter_and_timer_reset(monkeypatch):
    class Process:
        pid=123
        returncode=0
        def __init__(self,*args,**kwargs): self.calls=0
        def communicate(self,timeout=None):
            self.calls+=1
            if self.calls<3: raise subprocess.TimeoutExpired('test',timeout)
            return 'markdown',''
    ticks=iter([1000,1000,1601,1601,2202,2202,2202,9000,9000,9001,9001,9002,9002,9002])
    monkeypatch.setattr(archive.subprocess,'Popen',Process)
    monkeypatch.setattr(archive.time,'monotonic',lambda:next(ticks))
    output=io.StringIO();output.isatty=lambda:True
    for name in ('Marker','pymupdf4llm'):
        assert archive.run_converter(['test'],converter=name,output=output).stdout=='markdown'
    value=output.getvalue()
    assert 'Marker · 10:01 · Running' in value
    assert 'pymupdf4llm · 00:00 · Running' in value
    assert 'activity unmeasured' in value
    assert value.count('\n')==2
    assert '\r\x1b[2K' in value
    assert '%' not in value


def test_noninteractive_events():
    output=io.StringIO()
    result=archive.run_converter([sys.executable,'-c','print("ok")'],converter='Marker',output=output)
    assert result.returncode==0
    assert len(output.getvalue().splitlines())==2
    assert '\r' not in output.getvalue()


def test_failed_reimport_only_retries_conversion(tmp_path,monkeypatch):
    from stock.core import Store
    source=tmp_path/'source.pdf';source.write_bytes(b'original PDF')
    store=Store(tmp_path/'db')
    monkeypatch.setattr(archive,'read_document',lambda p:('Annual Report 2025',{}))
    monkeypatch.setattr(archive,'convert_pdf',lambda *a:(_ for _ in ()).throw(ValueError('failure')))
    first=archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    monkeypatch.setattr(archive,'read_document',lambda *a:(_ for _ in ()).throw(AssertionError('identification repeated')))
    def convert(src,dest):
        assert str(src)==first['original']
        dest.write_text('# Converted');return 'fixture'
    monkeypatch.setattr(archive,'convert_pdf',convert)
    second=archive.import_document(store,'700.HK',source,interactive=False)
    assert second['id']==first['id']
    assert second['source_sha256']==archive.filehash(source)
    assert second['original']==first['original']
    assert len(archive.documents(store,'700.HK'))==1
    monkeypatch.setattr(archive,'convert_pdf',lambda *a:(_ for _ in ()).throw(AssertionError('reconverted')))
    monkeypatch.setattr(archive,'read_document',lambda p:('Annual Report 2025',{}))
    archive.import_document(store,'700.HK',source,interactive=False)


def test_text_fallback_is_labeled(tmp_path,monkeypatch):
    monkeypatch.setattr(archive.shutil,'which',lambda *a:None)
    monkeypatch.setattr(archive,'pdf_python',lambda:sys.executable)
    def run(command,**kwargs):
        if kwargs['converter']=='pymupdf4llm': return subprocess.CompletedProcess(command,1,'','unavailable')
        return subprocess.CompletedProcess(command,0,'Extracted text','')
    monkeypatch.setattr(archive,'run_converter',run)
    destination=tmp_path/'out.md'
    assert 'text-only' in archive.convert_pdf(tmp_path/'in.pdf',destination)
    assert 'Text-only fallback' in destination.read_text()


def test_interrupt_kills_process_group_and_restores_line(monkeypatch):
    import signal
    class Process:
        pid=12345
        def __init__(self,*a,**kw): self.calls=0
        def communicate(self,**kw):
            self.calls+=1
            if self.calls==1: raise KeyboardInterrupt
            return '',''
    killed=[]
    monkeypatch.setattr(archive.subprocess,'Popen',Process)
    monkeypatch.setattr(archive.os,'killpg',lambda *args:killed.append(args))
    output=io.StringIO();output.isatty=lambda:True
    import pytest
    with pytest.raises(KeyboardInterrupt): archive.run_converter(['converter'],output=output)
    assert killed==[(12345,signal.SIGKILL)]
    assert output.getvalue().endswith('Interrupted\n')


def test_timer_starts_after_process_spawn_and_resets_per_document(monkeypatch):
    clock=[42]
    class Process:
        pid=123
        returncode=0
        def __init__(self,*a,**kw): clock[0]+=900
        def communicate(self,**kw): return '',''
    monkeypatch.setattr(archive.subprocess,'Popen',Process)
    monkeypatch.setattr(archive.time,'monotonic',lambda:clock[0])
    output=io.StringIO()
    for _ in range(2):
        clock[0]+=5000  # identification, download and archive time
        archive.run_converter(['test'],converter='Marker',output=output)
    assert output.getvalue().count('Marker · 00:00 · Running')==2
    assert output.getvalue().count('Marker · 00:00 · Completed')==2


def test_real_interrupt_cleans_descendants(tmp_path):
    import os
    import signal
    import time
    pidfile=tmp_path/'child.pid'
    child='import subprocess,sys,time; from pathlib import Path; p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"]); Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(60)'
    driver='from stock.archive import run_converter; import sys; run_converter([sys.executable,"-c",'+repr(child)+',sys.argv[1]])'
    process=subprocess.Popen([sys.executable,'-c',driver,str(pidfile)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    descendant=None
    try:
        deadline=time.monotonic()+5
        while not pidfile.exists() and time.monotonic()<deadline: time.sleep(.02)
        descendant=int(pidfile.read_text())
        process.send_signal(signal.SIGINT)
        _,error=process.communicate(timeout=5)
        assert b'Interrupted' in error
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            result=subprocess.run(['ps','-o','stat=','-p',str(descendant)],capture_output=True,text=True)
            if not result.stdout.strip() or result.stdout.strip().startswith('Z'): break
            time.sleep(.02)
        else: raise AssertionError('converter descendant survived cancellation')
    finally:
        if process.poll() is None: process.kill();process.wait()
        if descendant:
            try: os.kill(descendant,signal.SIGKILL)
            except ProcessLookupError: pass


def test_interrupted_import_preserves_archived_original(tmp_path,monkeypatch):
    import pytest
    from stock.core import Store
    store=Store(tmp_path/'db')
    source=tmp_path/'source.pdf';source.write_bytes(b'original')
    monkeypatch.setattr(archive,'read_document',lambda p:('Annual Report 2025',{}))
    def interrupt(*a): raise KeyboardInterrupt
    monkeypatch.setattr(archive,'convert_pdf',interrupt)
    with pytest.raises(KeyboardInterrupt):
        archive.import_document(store,'700.HK',source,root=tmp_path/'Research',interactive=False)
    doc,=archive.documents(store,'700.HK')
    assert doc['conversion_status']=='failed'
    assert archive.filehash(doc['original'])==archive.filehash(source)==doc['source_sha256']
    assert doc['markdown'] is None
