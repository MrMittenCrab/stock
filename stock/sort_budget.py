"""One monotonic budget across preparation, retries, review and publication."""
from contextvars import ContextVar
import time
import math

CURRENT=ContextVar('sort_budget',default=None)

class BudgetExceeded(RuntimeError):
    pass

class Budget:
    def __init__(self,document_seconds=720,command_seconds=1200,requests=12,request_seconds=120):
        if any(not math.isfinite(v) or v<=0 for v in (document_seconds,command_seconds,requests,request_seconds)):
            raise ValueError('Sort budgets must be positive')
        self.document_seconds=document_seconds;self.command_end=time.monotonic()+command_seconds
        self.requests=requests;self.request_seconds=request_seconds
        self.documents={};self.document=None;self.request_end=None;self.request_deadlines={}
    def __enter__(self):
        self.token=CURRENT.set(self);return self
    def __exit__(self,*args):CURRENT.reset(self.token)
    def use_document(self,ident):
        self.document=ident
        self.documents.setdefault(ident,[time.monotonic()+self.document_seconds,0])
        self.request_end=None;self.check()
    def remaining(self):
        ends=[self.command_end]
        if self.document is not None:ends.append(self.documents[self.document][0])
        return min(ends)-time.monotonic()
    def check(self):
        if self.remaining()<=0:raise BudgetExceeded('Time limit')
    def request(self,key=None):
        self.check()
        if self.document is None:self.use_document('Insights')
        state=self.documents[self.document]
        if state[1]>=self.requests:raise BudgetExceeded('Request limit')
        state[1]+=1
        deadline=min(time.monotonic()+self.request_seconds,time.monotonic()+self.remaining())
        if key is not None:
            deadline=self.request_deadlines.setdefault((self.document,key),deadline)
        self.request_end=deadline
        self.timeout(self.request_seconds)
    def timeout(self,requested):
        self.check()
        ends=[time.monotonic()+requested,time.monotonic()+self.remaining()]
        if self.request_end is not None:ends.append(self.request_end)
        remaining=min(ends)-time.monotonic()
        if remaining<=0:raise BudgetExceeded('Request timeout')
        return remaining

def check():
    budget=CURRENT.get()
    if budget:budget.check()


from contextlib import contextmanager
WAITING=ContextVar("sort_operator_waiting",default=False)

@contextmanager
def operator_wait():
    """Exclude deliberate human review from every processing deadline."""
    if WAITING.get():
        yield
        return
    token=WAITING.set(True)
    budget=CURRENT.get();started=time.monotonic()
    try:yield
    finally:
        WAITING.reset(token)
        if budget:
            elapsed=time.monotonic()-started
            budget.command_end+=elapsed
            for state in budget.documents.values():state[0]+=elapsed
            if budget.request_end is not None:budget.request_end+=elapsed
            budget.request_deadlines={k:v+elapsed for k,v in budget.request_deadlines.items()}
