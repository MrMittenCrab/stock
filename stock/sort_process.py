"""Single-line terminal status and cancellable Cursor process groups."""
import os
import re
import signal
import subprocess
import sys
import threading
import time

ACTIVE_PROCESS = None

class DeferredCursor:
    """Completed staging can be inspected without starting or authenticating Cursor."""
    def __init__(self,factory):
        self.factory=factory;self.cursor=None;self.record_metrics=None

    @property
    def supports_distillation(self):
        return getattr(self.factory,'supports_distillation',False) is True

    def extract(self,unit,context):
        from .sort_budget import CURRENT
        budget=CURRENT.get()
        if budget:
            import hashlib,json
            identity={k:v for k,v in unit.items() if k!='retry'}
            stable_context=context.split('\nClarification:',1)[0] if isinstance(context,str) else context
            key=hashlib.sha256(json.dumps([identity,stable_context],sort_keys=True).encode()).hexdigest()
            budget.request(key)
        if self.cursor is None:self.cursor=self.factory()
        self.cursor.record_metrics=self.record_metrics
        return self.cursor.extract(unit,context)


class Status:
    def __init__(self):
        self.message='Preparing';self.stage='Prepare';self.preview_counts=None;self.started=time.monotonic();self.stage_started=self.started;self.document=None;self.section=None;self.stop=threading.Event();self.reviewing=False
    def __call__(self,message):
        if message!=self.message:self.stage_started=time.monotonic()
        from .sort_budget import check
        check()
        self.message=message
        fields=message.split(' · ')
        if fields[0].isdigit():
            if self.document!=fields[0]:self.section=None
            self.document=fields[0]
        match=re.search(r'(?:section |batch )(\d+/\d+)',message)
        if match:self.section=match[1]
        for needle,label in [('semantic review','Review'),('citation recovery','Citations'),('document distillation','Distill'),('selection','Reconstruct'),('preparation','Prepare'),('Semantic comparison','Group'),('Sorting','Prepare'),('validation','Verify')]:
            if needle in message:
                self.stage=label;break
        self.reviewing=False
        self.log_event(dict(message=message))
    def log_event(self,event):
        if hasattr(self,'log'):
            import json
            self.log.write(json.dumps(dict(elapsed=time.monotonic()-self.started,**event),ensure_ascii=False)+'\n');self.log.flush()

    def review(self,message):
        if not self.reviewing and sys.stdout.isatty(): print()
        self.reviewing=True
        self.log_event(dict(review=message))
        print(message,flush=True)
    def review_all(self,message):
        self.reviewing=True
        if sys.stdout.isatty() and sys.stdin.isatty():
            # stdlib plain pager: keyboard paging, independent of PAGER settings.
            import pydoc, shutil, textwrap
            width=max(20,shutil.get_terminal_size().columns-1)
            wrapped='\n'.join(textwrap.fill(line,width=width,replace_whitespace=False) for line in message.split('\n'))
            pydoc.ttypager('Space: next · Enter: line · b: back · q: return to approval\n'+wrapped)
        else:
            print(message,flush=True)

    def line(self,width=None):
        elapsed=int(time.monotonic()-self.started)
        line=f'{self.document or "Stock"} · {self.section or "0/0"} · {self.stage} · {elapsed//60:02}:{elapsed%60:02}'
        return line if width is None else line[:max(1,width-1)]

    def __enter__(self):
        from .core import ROOT
        import uuid
        directory=ROOT/'.data'/'sort-logs';directory.mkdir(parents=True,exist_ok=True)
        self.log_path=directory/(uuid.uuid4().hex+'.jsonl')
        self.log=self.log_path.open('a')
        self.log_event(dict(diagnostics='Detailed selections, reviews, exclusions and exact references remain in source_work_v3/source_model_calls in the local Stock database.'))
        def refresh():
            while not self.stop.wait(.5):
                if sys.stdout.isatty() and not self.reviewing:
                    width=__import__('shutil').get_terminal_size().columns
                    line=self.line(width)
                    print('\r'+line[:max(1,width-1)].ljust(max(1,width-1)),end='',flush=True)
        self.thread=threading.Thread(target=refresh,daemon=True);self.thread.start();return self
    def __exit__(self,*args):
        self.stop.set();self.thread.join()
        if sys.stdout.isatty(): print()
        self.log.close()


def run(command,**kwargs):
    global ACTIVE_PROCESS
    kwargs.pop('capture_output',None);timeout=kwargs.pop('timeout',120)
    from .sort_budget import CURRENT, BudgetExceeded
    budget=CURRENT.get()
    if budget:timeout=budget.timeout(timeout)
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,**kwargs)
    ACTIVE_PROCESS=process
    try:
        stdout,stderr=process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(command,process.returncode,stdout,stderr)
    except BaseException as exc:
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try: process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.communicate()
        if isinstance(exc,subprocess.TimeoutExpired) and budget:
            raise BudgetExceeded('Time limit' if budget.remaining()<=0 else 'Request timeout') from exc
        raise
    finally:
        ACTIVE_PROCESS=None
