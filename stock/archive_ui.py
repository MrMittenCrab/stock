"""Keyboard-only flat archive with metadata expanded in place."""
import os
import json
import shlex
import subprocess
import sys
import textwrap
from datetime import date
from pathlib import Path

from rich.text import Text
from rich.cells import cell_len, set_cell_size
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from .archive import documents
from .native import NATIVE_CSS
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
    CSS=NATIVE_CSS+'''
    Screen { background: ansi_default; color: ansi_default; padding: 1 1; }
    Static { height: auto; }
    #heading { margin-bottom: 1; }
    #rows { height: 1fr; scrollbar-size: 0 0; }
    #help { margin-top: 1; }
    '''

    def __init__(self,ticker,store):
        super().__init__(ansi_color=True)
        self.store=store
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
                         ('Conversion',doc.get('quality_status',doc['conversion_status'])),('Sorted','Yes' if doc['sorted_at'] else 'No')]
                details.append(('Published',doc['publication_date'] or 'Unknown'))
                structured=json.loads(doc.get('structured_metadata') or '{}')
                provenance=json.loads(doc.get('metadata_provenance') or '{}')
                for field,label in (('filing_date','Filed'),('document_date','Document'),('event_date','Event'),('report_period_end','Period end')):
                    if structured.get(field):
                        details.append((label,structured[field]))
                        basis=structured.get(field+'_basis') or provenance.get(field,{}).get('basis')
                        evidence=structured.get(field+'_evidence_url') or provenance.get(field,{}).get('evidence_url')
                        if basis: details.append(('Basis',basis))
                        if evidence: details.append(('Source',evidence))
                publication=provenance.get('date',{})
                if publication.get('basis'): details.append(('Pub basis',publication['basis']))
                if publication.get('url') or publication.get('evidence_url'): details.append(('Pub source',publication.get('url') or publication['evidence_url']))
                if doc['conversion_error']: details.append(('Error',doc['conversion_error']))
                for key,value in details:
                    detail=f'    {key:<10} {value}'
                    lines.extend(textwrap.wrap(detail,width=width,subsequent_indent='    ') if width<55 else [detail])
            rendered=Text('\n'.join(lines),no_wrap=True,overflow='ellipsis')
            self.query_one(f'#doc-{i}',Static).update(rendered)
        self.query_one('#help',Static).update(Text('↑↓ Navigate   Space '+('Collapse' if self.selected in self.expanded else 'Expand')+'   O Original   M Markdown   Esc Quit',no_wrap=False))

    async def on_key(self,event):
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
