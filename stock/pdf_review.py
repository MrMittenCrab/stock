"""Bounded, local Marker review; deliberately has no Archive/Sort publication path."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def page_range(value):
    try:
        pages=[int(n) for n in value.split(',')]
        if not pages or min(pages)<1: raise ValueError
    except ValueError:
        raise ValueError('Pages must be comma-separated positive PDF page numbers') from None
    return ','.join(str(n-1) for n in sorted(set(pages)))


def validate_paths(source,output):
    source=Path(source).resolve();output=Path(output).resolve()
    if not source.is_file() or source.suffix.lower()!='.pdf':
        raise ValueError('Source must be an existing PDF')
    if output.exists(): raise ValueError('Review output must not already exist')
    root=Path(__file__).resolve().parents[1]
    if output.is_relative_to(source.parent) or any(output.is_relative_to(root/p) for p in ('Research','.data')):
        raise ValueError('Review output must be outside source, Research and production data directories')
    return source,output


def marker_config(profile,pages):
    config={'mode':'balanced' if profile=='high-fidelity' else 'fast','force_ocr':profile=='high-fidelity','use_llm':False,
            'paginate_output':True,'disable_tqdm':True}
    if pages: config['page_range']=[int(n) for n in page_range(pages).split(',')]
    return config


def process_rows():
    result=subprocess.run(['ps','-axo','pid=,ppid=,pgid=,rss=,args='],capture_output=True,text=True,check=True)
    return [line.split(None,4) for line in result.stdout.splitlines() if len(line.split(None,4))==5]


def monitor(child,seconds,rss_mib):
    start=time.monotonic();peak=0;shared_peak=0;limit=None
    try:
        while child.poll() is None:
            rows=process_rows()
            # Only this newly-created process group is owned by the review.
            own=sum(int(r[3]) for r in rows if int(r[2])==child.pid)
            shared=sum(int(r[3]) for r in rows if int(r[2])!=child.pid and
                       any(s in r[4] for s in ('/llama-server ','-m surya.fast_layout.server ','-m surya.ocr_error.server ')))
            peak=max(peak,own);shared_peak=max(shared_peak,shared)
            if time.monotonic()-start>seconds: limit='time limit'
            elif own+shared>rss_mib*1024: limit='sampled process and shared-service RSS limit'
            if limit: break
            time.sleep(.2)
    finally:
        if child.poll() is None:
            # Never signal pre-existing inference servers or unrelated groups.
            try: os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError: pass
        child.wait()
    return {'elapsed_seconds':round(time.monotonic()-start,2),'peak_process_group_rss_mib':round(peak/1024,1),
            'peak_shared_service_rss_mib':round(shared_peak/1024,1),'limit':limit,'returncode':child.returncode,
            'memory_scope':'sampled RSS, includes shared service processes; excludes Metal/GPU allocations'}


def convert(source,output,*,profile='high-fidelity',pages=None,python=None,seconds=1800,rss_mib=8192):
    if not math.isfinite(seconds) or not 0<seconds<=3600: raise ValueError('Seconds must be >0 and <=3600')
    if not math.isfinite(rss_mib) or not 0<rss_mib<=8192: raise ValueError('RSS limit must be >0 and <=8192 MiB')
    if profile not in ('current','high-fidelity'): raise ValueError('Unknown review profile')
    source,output=validate_paths(source,output)
    config=marker_config(profile,pages)
    python=Path(python or Path.home()/'.venvs/marker/bin/python').expanduser().absolute()
    if not python.is_file(): raise ValueError('Installed Marker Python not found')
    digest=sha256(source)
    output.mkdir(parents=True,exist_ok=False)
    (output/'config.json').write_text(json.dumps(config,indent=2))
    worker=Path(__file__).with_name('marker_review_worker.py')
    command=[str(python),'-u',str(worker),str(source),str(output)]
    env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',
             OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',FAST_LAYOUT_NUM_THREADS='2',
             SURYA_INFERENCE_PARALLEL='1',SURYA_INFERENCE_AUTOSTART='false',
             FAST_LAYOUT_SERVER_AUTOSTART='false',OCR_ERROR_SERVER_AUTOSTART='false',DETECTOR_SERVER_AUTOSTART='false',
             SURYA_INFERENCE_TIMEOUT_SECONDS='120',SURYA_INFERENCE_STARTUP_TIMEOUT='120',NO_PROXY='127.0.0.1,localhost,::1')
    manifest={'output':str(output),'source':str(source),'source_sha256':digest,'profile':profile,'configuration':config,
              'pdf_pages':None if not pages else [n+1 for n in config['page_range']],
              'active_archive':False,'page_marker_indexing':'Marker {n} is zero-based; PDF page = n + 1',
              'command':command,'seconds_limit':seconds,'rss_limit_mib':rss_mib,
              'network':'loopback only; offline weights; existing local inference services only'}
    status=output/'review.json'
    status.write_text(json.dumps(manifest,indent=2))
    try:
        with (output/'run.log').open('w') as log:
            child=subprocess.Popen(command,env=env,cwd=output,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            manifest.update(monitor(child,seconds,rss_mib))
        if sha256(source)!=digest: raise ValueError('Source changed during conversion')
        if manifest['returncode']==0 and not any(p.stat().st_size for p in output.rglob('*.md')):
            raise ValueError('Marker produced no nonempty Markdown')
        manifest['output_files']={str(p.relative_to(output)):sha256(p) for p in sorted(output.rglob('*'))
                                  if p.is_file() and p.name not in ('review.json','run.log')}
        versions=output/'versions.json'
        if versions.exists(): manifest['versions']=json.loads(versions.read_text())
    except BaseException as exc:
        manifest['error']=str(exc)
        raise
    finally:
        status.write_text(json.dumps(manifest,indent=2))
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--profile',choices=('current','high-fidelity'),default='high-fidelity')
    parser.add_argument('--pages',help='One-based PDF page numbers, e.g. 4,5,6,14,15; omitted means all')
    parser.add_argument('--python',type=Path,help='Already installed Marker Python')
    parser.add_argument('--seconds',type=float,default=1800)
    parser.add_argument('--rss-mib',type=float,default=8192)
    args=parser.parse_args()
    try:
        result=convert(**vars(args))
        print(json.dumps({key:result.get(key) for key in ('output','profile','returncode','elapsed_seconds','limit','active_archive')}))
        return 0 if result['returncode']==0 else 1
    except (ValueError,OSError) as exc:
        parser.exit(1,f'Review failed: {exc}\n')


if __name__=='__main__':
    raise SystemExit(main())
