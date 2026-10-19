"""Keyboard-only flat archive with metadata expanded in place."""
import os
import shlex
import subprocess
import sys
import textwrap
from datetime import date
from pathlib import Path

from rich.text import Text
from rich.cells import cell_len, set_cell_size
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Static, Input

from .archive import documents, update_metadata, TYPES
from .core import symbol


def open_file(path,markdown=False):
    if not path or not Path(path).is_file():
        raise ValueError('Markdown unavailable' if markdown else 'Original file unavailable')
    configured=os.environ.get('STOCK_MARKDOWN_VIEWER') if markdown else None
    command=shlex.split(configured) if configured else (['open'] if sys.platform=='darwin' else ['xdg-open'])
    if not command: raise ValueError('STOCK_MARKDOWN_VIEWER must name an executable')
    result=subprocess.run([*command,str(path)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=30)
    if result.returncode: raise ValueError('Viewer failed to open the file')


class ArchiveApp(App):
    AUTO_FOCUS=''
    ENABLE_COMMAND_PALETTE=False
    BINDINGS=[('escape','quit','')]
    CSS='''
    Screen { background: #111111; color: #dddddd; padding: 1 1; }
    Static { height: auto; }
    #heading { margin-bottom: 1; }
    #rows { height: 1fr; scrollbar-size: 0 0; }
    #help { margin-top: 1; }
    #editor { display: none; height: auto; max-height: 60%; scrollbar-size: 0 0; }
    .edit-row { height: 1; }
    .edit-label { width: 12; }
    Input { width: 1fr; min-width: 0; height: 1; border: none; padding: 0; background: #1e1e1e; }
    Input:focus { border: none; background: #333333; }
    '''

    def __init__(self,ticker,store):
        super().__init__()
        self.store=store
        self.editing=False
        self.ticker=symbol(ticker)
        self.docs=documents(store,self.ticker)
        self.selected=0
        self.expanded=set()

    def compose(self) -> ComposeResult:
        yield Static('STOCK · ARCHIVE',id='heading')
        yield Static(self.ticker,id='ticker')
        with VerticalScroll(id='rows',can_focus=False):
            if not self.docs: yield Static('No archived documents')
            for i in range(len(self.docs)):
                yield Static('',id=f'doc-{i}')
        with VerticalScroll(id='editor'):
            yield Static('Type · '+ ' · '.join(f'{i} {t}' for i,t in enumerate(TYPES,1)))
            for key,label in (('type','Type'),('period','Period'),('date','Date'),('title','Title'),('publisher','Publisher')):
                with Horizontal(classes='edit-row'):
                    yield Static(label,classes='edit-label')
                    yield Input(placeholder='Unknown',id='edit-'+key)
        yield Static('',id='status')
        yield Static('',id='help')

    def on_mount(self): self.paint()
    def on_resize(self):
        if self.is_mounted: self.paint()

    def paint(self):
        width=max(1,self.size.width-2)
        type_width=max([len(d['type']) for d in self.docs]+[7])
        descriptor_width=max(8,min(28,width-16-type_width-12))
        for i,doc in enumerate(self.docs):
            published=date.fromisoformat(doc['publication_date']).strftime('%d %b %Y').upper() if doc['publication_date'] else 'Unknown'
            descriptor=doc['period'] or doc['title']
            # Keep identical column starts for every document, including expansion.
            descriptor=set_cell_size(descriptor,descriptor_width) if cell_len(descriptor)<=descriptor_width else set_cell_size(descriptor,descriptor_width-1)+'…'
            formats=[]
            if doc['original'] and Path(doc['original']).exists(): formats.append(Path(doc['original']).suffix[1:].upper())
            if doc['markdown'] and doc['markdown']!=doc['original'] and Path(doc['markdown']).exists(): formats.append('MD')
            line=f"{'> ' if i==self.selected else '  '}{published:<11}  {doc['type']:<{type_width}}  {descriptor}  {' · '.join(formats)}"
            if width<55:
                line=f"{'> ' if i==self.selected else '  '}{doc['type']}  {doc['period'] or doc['title']}"
                lines=textwrap.wrap(line,width=width,subsequent_indent='  ') or ['']
                lines+=textwrap.wrap(f"  {published}  {' · '.join(formats)}",width=width,subsequent_indent='  ')
            else:
                lines=[line]
            if i in self.expanded:
                details=[('Title',doc['title']),('Publisher',doc['publisher'] or 'Unknown'),
                         ('Original',Path(doc['original']).name if doc['original'] else 'Unavailable'),
                         ('Markdown',Path(doc['markdown']).name if doc['markdown'] and Path(doc['markdown']).is_file() else 'Unavailable'),
                         ('Conversion',doc['conversion_status']),('Sorted','Yes' if doc['sorted_at'] else 'No')]
                if doc['conversion_error']: details.append(('Error',doc['conversion_error']))
                for key,value in details:
                    detail=f'    {key:<10} {value}'
                    lines.extend(textwrap.wrap(detail,width=width,subsequent_indent='    ') if width<55 else [detail])
            rendered=Text('\n'.join(lines),no_wrap=True,overflow='ellipsis')
            self.query_one(f'#doc-{i}',Static).update(rendered)
        self.query_one('#help',Static).update(Text('↑↓ Navigate   Space '+('Collapse' if self.selected in self.expanded else 'Expand')+'   E Edit   O Original   M Markdown   Esc Quit',no_wrap=False))

    async def on_key(self,event):
        if self.editing:
            if event.key=='escape':
                event.stop();event.prevent_default();self.close_editor()
            elif event.key=='enter':
                event.stop();event.prevent_default()
                self.save_editor()
            return
        event.stop();event.prevent_default()
        if event.key=='escape': self.exit();return
        if event.key in ('pageup','pagedown'):
            rows=self.query_one('#rows',VerticalScroll)
            if event.key=='pageup': rows.scroll_page_up()
            else: rows.scroll_page_down()
            return
        if not self.docs: return
        if event.key in ('up','down'):
            self.selected=max(0,min(len(self.docs)-1,self.selected+(-1 if event.key=='up' else 1)))
        elif event.key.lower()=='e':
            self.editing=True
            doc=self.docs[self.selected]
            self.edit_doc=doc
            for key in ('type','period','date','title','publisher'):
                field=self.query_one('#edit-'+key,Input)
                field.value=(doc['publication_date'] if key=='date' else doc[key]) or ''
            self.query_one('#editor').display=True
            self.query_one('#edit-type',Input).focus()
            self.query_one('#status',Static).update('Tab Next · Enter Save · Esc Cancel · Blank Unknown')
            return
        elif event.key=='space':
            if self.selected in self.expanded: self.expanded.remove(self.selected)
            else: self.expanded.add(self.selected)
        elif event.key.lower() in ('o','m'):
            markdown=event.key.lower()=='m'
            try:
                import asyncio
                await asyncio.to_thread(open_file,self.docs[self.selected]['markdown' if markdown else 'original'],markdown)
                self.query_one('#status',Static).update('')
            except (OSError,ValueError,subprocess.SubprocessError) as exc:
                self.query_one('#status',Static).update(Text(str(exc)))
        self.paint()
        self.query_one(f'#doc-{self.selected}').scroll_visible()

    def close_editor(self):
        self.editing=False
        self.query_one('#editor').display=False
        self.set_focus(None)
        self.query_one('#status',Static).update('')
        self.paint()

    def save_editor(self):
        import sqlite3
        doc=self.edit_doc
        changes={}
        for key in ('type','period','date','title','publisher'):
            value=self.query_one('#edit-'+key,Input).value.strip()
            value=None if value.lower() in ('','unknown') else value
            if key=='type':
                if value and value.isdigit() and 1<=int(value)<=len(TYPES): value=TYPES[int(value)-1]
                value=next((t for t in TYPES if value and t.lower()==value.lower()),value) or 'Unknown'
            old=doc['publication_date'] if key=='date' else doc[key]
            if value!=old: changes[key]=value
        try:
            updated=update_metadata(self.store,doc,changes) if changes else doc
        except (OSError,ValueError,sqlite3.Error) as exc:
            self.query_one('#status',Static).update(Text(str(exc)))
            return
        self.docs=documents(self.store,self.ticker)
        self.selected=next(i for i,d in enumerate(self.docs) if d['id']==updated['id'])
        self.close_editor()
