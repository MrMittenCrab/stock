"""Keyboard-only Sources with inline evidence, topic editing and file filtering."""
import asyncio
import subprocess
import sqlite3
from datetime import date
from pathlib import Path
from rich.console import Console
from rich.text import Text
from rich.cells import cell_len, set_cell_size
from textual.app import App
from textual.containers import VerticalScroll
from textual.widgets import Static
from .archive import documents
from .archive_ui import open_file
from .core import symbol
from .native import NATIVE_CSS
from . import sources


def passage_lines(passage,width,expanded=False,selected=False):
    published=date.fromisoformat(passage['publication_date']).strftime('%d %b %Y').upper() if passage['publication_date'] else 'Unknown'
    prefix=f"{'> ' if selected else '  '}{published:<11}  {passage['category']:<10}  "
    column=cell_len(prefix)
    available=max(1,width-column)
    # Rich wrapping uses terminal cells, including wide characters and combining marks.
    original=Text(passage['text'])
    if expanded:
        lines=[line.plain for line in original.wrap(Console(),available,overflow='fold')]
    else:
        text=' '.join(passage['text'].split())
        lines=[text if cell_len(text)<=available else set_cell_size(text,max(0,available-1))+'…']
    return [prefix+(lines[0] if lines else '')]+[' '*column+line for line in lines[1:]]


class SourcesApp(App):
    AUTO_FOCUS=''
    ENABLE_COMMAND_PALETTE=False
    BINDINGS=[('escape','quit','')]
    CSS=NATIVE_CSS+'''
    Screen { padding: 1 1; }
    Static { height: auto; }
    #heading { margin-bottom: 1; }
    #rows { height: 1fr; scrollbar-size: 0 0; }
    #help { margin-top: 1; }
    '''

    def __init__(self,ticker,store):
        super().__init__(ansi_color=True)
        self.ticker=symbol(ticker);self.store=store
        self.docs=documents(store,self.ticker)
        self.all_passages=sources.passages(store,self.ticker)
        self.topic=None;self.selected=0;self.topic_index=0
        self.expanded=set();self.editing=None
        self.files=False;self.file_index=0;self.document_id=None
        self.message=''
        self.row_widgets=[]

    def compose(self):
        yield Static('STOCK · SOURCES',id='heading')
        yield Static(self.ticker,id='ticker')
        yield VerticalScroll(id='rows',can_focus=False)
        yield Static('',id='status')
        yield Static('',id='help')

    async def on_mount(self): await self.paint()
    async def on_resize(self):
        if self.is_mounted: await self.paint()

    def filtered(self):
        return [p for p in self.all_passages if self.document_id is None or p['document_id']==self.document_id]

    def visible(self):
        return [p for p in self.filtered() if (self.topic in p['topics'] if self.topic!='Unclassified' else not p['topics']) or p['id']==self.editing]

    async def paint(self):
        rows=self.query_one('#rows',VerticalScroll)
        old_scroll=rows.scroll_y
        await rows.remove_children()
        self.row_widgets=[];focus=None
        width=max(1,self.size.width-2)
        self.query_one('#heading',Static).update('STOCK · SOURCES'+(' · '+self.topic.upper() if self.topic else ''))
        def add(text):
            widget=Static(Text(text,no_wrap=True,overflow='crop'))
            self.row_widgets.append(widget)
            return widget
        if self.files:
            options=[(None,'All')]+[(d['id'],Path(d['original']).name if d['original'] else d['title']) for d in self.docs]
            first=max(0,min(self.file_index-2,len(options)-5))
            for i in range(first,min(len(options),first+5)):
                ident,label=options[i]
                w=add(('> ' if i==self.file_index else '  ')+label)
                if i==self.file_index: focus=w
        if self.topic is None:
            counts={t:0 for t in (*sources.TOPICS,'Unclassified')}
            for p in self.filtered():
                for t in p['topics'] or {'Unclassified'}: counts[t]+=1
            for i,t in enumerate(counts):
                w=add(f"{'> ' if i==self.selected and not self.files else '  '}{t:<16} {counts[t]:>5}")
                if i==self.selected and not self.files: focus=w
        else:
            visible=self.visible()
            self.selected=max(0,min(self.selected,len(visible)-1))
            for i,p in enumerate(visible):
                chosen=i==self.selected
                w=add('\n'.join(passage_lines(p,width,p['id'] in self.expanded,chosen and not self.editing and not self.files)))
                if chosen and not self.editing and not self.files: focus=w
                if p['id']==self.editing:
                    for j,t in enumerate(sources.TOPICS):
                        w=add(f"{'> ' if j==self.topic_index else '  '}[{'x' if t in p['topics'] else ' '}] {t}")
                        if j==self.topic_index and not self.files: focus=w
            if not visible: add('No passages')
        await rows.mount(*self.row_widgets)
        rows.scroll_to(y=old_scroll,animate=False,force=True)
        if focus: focus.scroll_visible(animate=False)
        status=self.message
        if self.document_id is not None:
            doc=next(d for d in self.docs if d['id']==self.document_id)
            status=('File · '+Path(doc['original']).name+'\n'+status).rstrip()
        self.query_one('#status',Static).update(Text(status))
        self.query_one('#status').display=bool(status)
        if self.files: help_text='↑↓ Navigate   → Select   F Close   Esc Quit'
        elif self.editing: help_text='↑↓ Navigate   Space Toggle   T Close   Esc Quit'
        elif self.topic:
            p=self.visible()[self.selected] if self.visible() else None
            help_text='↑↓ Navigate   Space '+('Collapse' if p and p['id'] in self.expanded else 'Expand')+'   T Topics   O Source\nF Files   ← Back   Esc Quit'
        else: help_text='↑↓ Navigate   → Open   F Files   Esc Quit'
        self.query_one('#help',Static).update(Text(help_text))

    def close_topics(self):
        # Keep the same row index if removal makes this passage leave the filter.
        self.editing=None
        if self.topic: self.selected=max(0,min(self.selected,len(self.visible())-1))

    async def on_key(self,event):
        event.stop();event.prevent_default()
        key=event.key.lower()
        if key=='escape': self.exit();return
        if key in ('pageup','pagedown'):
            rows=self.query_one('#rows',VerticalScroll)
            if key=='pageup': rows.scroll_page_up()
            else: rows.scroll_page_down()
            return
        if key=='f':
            if not self.files:
                self.file_index=next(i for i,v in enumerate([None]+[d['id'] for d in self.docs]) if v==self.document_id)
            self.files=not self.files
        elif self.files:
            if key in ('up','down'): self.file_index=max(0,min(len(self.docs),self.file_index+(-1 if key=='up' else 1)))
            elif key in ('right','enter','space'):
                self.document_id=([None]+[d['id'] for d in self.docs])[self.file_index]
                self.files=False;self.close_topics();self.selected=0
            elif key=='left': self.files=False
        elif self.editing:
            if key=='t': self.close_topics()
            elif key in ('up','down'): self.topic_index=max(0,min(7,self.topic_index+(-1 if key=='up' else 1)))
            elif key=='space':
                p=next(p for p in self.all_passages if p['id']==self.editing)
                t=sources.TOPICS[self.topic_index]
                try:
                    sources.set_topic(self.store,p['id'],t,t not in p['topics'])
                    if t in p['topics']: p['topics'].remove(t)
                    else: p['topics'].add(t)
                except (ValueError,sqlite3.Error) as exc: self.message=str(exc)
            elif key=='left': self.close_topics()
        elif key in ('up','down'):
            count=9 if self.topic is None else len(self.visible())
            self.selected=max(0,min(count-1,self.selected+(-1 if key=='up' else 1)))
        elif self.topic is None:
            if key in ('right','enter'):
                self.topic=(*sources.TOPICS,'Unclassified')[self.selected];self.selected=0
        elif key=='left':
            self.selected=(*sources.TOPICS,'Unclassified').index(self.topic);self.topic=None;self.message=''
        elif self.visible():
            p=self.visible()[self.selected]
            if key=='space':
                if p['id'] in self.expanded: self.expanded.remove(p['id'])
                else: self.expanded.add(p['id'])
            elif key=='t': self.editing=p['id'];self.topic_index=0
            elif key=='o':
                doc=next(d for d in self.docs if d['id']==p['document_id'])
                loc=p['location'];reference=(f"Page {loc['page']}"+(f"–{loc['page_end']}" if loc.get('page_end') else '')+' · ' if loc.get('page') else '')+(loc.get('section')+' · ' if loc.get('section') else '')+f"Characters {loc['start']+1}–{loc['end']}"
                provenance=p['date_provenance']
                self.message=' · '.join(filter(None,[doc['title'],p['speaker'] or p['category'],reference]))+'\n'+loc['verification']+'\nPublished · '+(p['publication_date'] or 'Unknown')+' · '+(provenance.get('basis') or provenance.get('status',''))
                url=provenance.get('evidence_url') or provenance.get('url')
                if url: self.message+='\n'+url
                try: await asyncio.to_thread(open_file,doc['original'])
                except (OSError,ValueError,subprocess.SubprocessError) as exc: self.message+='\n'+str(exc)
        await self.paint()
