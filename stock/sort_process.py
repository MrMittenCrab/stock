"""Single-line terminal status and cancellable Cursor process groups."""
import os
import signal
import subprocess
import sys
import threading
import time

ACTIVE_PROCESS = None

class Status:
    def __init__(self):
        self.message='Preparing';self.started=time.monotonic();self.stop=threading.Event();self.reviewing=False
    def __call__(self,message):
        self.message=message
        if self.reviewing or not sys.stdout.isatty(): print(message,flush=True)
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

    def __enter__(self):
        def refresh():
            while not self.stop.wait(.5):
                if sys.stdout.isatty() and not self.reviewing:
                    width=__import__('shutil').get_terminal_size().columns
                    alive=ACTIVE_PROCESS is not None and ACTIVE_PROCESS.poll() is None
                    line=f'{self.message} · {time.monotonic()-self.started:.0f}s · '+('child alive; activity is not progress' if alive else 'working')
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
