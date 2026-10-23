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
        if self.cursor is None:self.cursor=self.factory()
        self.cursor.record_metrics=self.record_metrics
        return self.cursor.extract(unit,context)


class Status:
    def __init__(self):
        self.message='Preparing';self.started=time.monotonic();self.stage_started=self.started;self.document=None;self.section=None;self.stop=threading.Event();self.reviewing=False
    def __call__(self,message):
        if message!=self.message:self.stage_started=time.monotonic()
        self.message=message
        fields=message.split(' · ')
        if fields[0].isdigit():
            self.document=fields[0]
            match=re.search(r'section (\d+/\d+)',message)
            if match:self.section=match[1]
        self.reviewing=False
        if not sys.stdout.isatty(): print(message,flush=True)
    def review(self,message):
        if not self.reviewing and sys.stdout.isatty(): print()
        self.reviewing=True
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
        now=time.monotonic()
        child=ACTIVE_PROCESS
        state=('running (waiting for result; progress unknown)' if child.poll() is None else 'exited') if child is not None else 'idle'
        timers=f'stage {now-self.stage_started:.0f}s · total {now-self.started:.0f}s · child {state}'
        line=f'{self.message} · {timers}'
        if width is not None and len(line)>=width:
            stage=self.message.split(' · ')[-1].replace('semantic review','review').replace('citation recovery','repair').replace('preparation','prep')
            child_state='running; progress unknown' if child is not None and child.poll() is None else ('exited' if child else 'idle')
            line=f'{self.document or "Stock"} · {self.section or "prep"} · {stage} · stage {now-self.stage_started:.0f}s · total {now-self.started:.0f}s · child {child_state}'
            if len(line)>=width:
                line=f'{self.document or "Stock"} {self.section or "prep"} {stage[:10]} · stage {now-self.stage_started:.0f}s total {now-self.started:.0f}s · child {child_state}'
        return line if width is None else line[:max(1,width-1)]

    def __enter__(self):
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


def run(command,**kwargs):
    global ACTIVE_PROCESS
    kwargs.pop('capture_output',None);kwargs.pop('timeout',None)
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,**kwargs)
    ACTIVE_PROCESS=process
    try:
        stdout,stderr=process.communicate(timeout=600)
        return subprocess.CompletedProcess(command,process.returncode,stdout,stderr)
    except BaseException:
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try: process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.communicate()
        raise
    finally:
        ACTIVE_PROCESS=None
