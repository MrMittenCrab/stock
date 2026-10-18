"""Compact monochrome price view. Chart x positions represent observations."""
import asyncio
import textwrap
from datetime import datetime
from rich.text import Text
from rich.style import Style
from textual.widgets.text_area import TextAreaTheme
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Static, TextArea
from .core import State, ZOOMS
from .data import DataError, HK, hk_date


def date_label(timestamp, minute=False):
    date = datetime.fromisoformat(timestamp.replace('Z','+00:00')).astimezone(HK)
    return date.strftime('%d %b %Y' + (' %H:%M HKT' if minute else '')).upper()


def chart(state, annotations, width, height):
    rows, start = state.window()
    w, h = max(12, width-12), max(5,height)
    values = [float(r['close']) for r in rows]
    low, high = min(values), max(values)
    if low == high:
        low -= max(abs(low)*0.001,0.01)
        high += max(abs(high)*0.001,0.01)
    grid = [[' ']*w for _ in range(h)]
    def x(i): return round(i*(w-1)/max(1,len(rows)-1))
    def y(v): return round((high-v)/(high-low)*(h-1))
    # Straight segments connect observed closes, never spline/smoothed prices.
    points = [(x(i), y(v)) for i,v in enumerate(values)]
    for i,(px,py) in enumerate(points):
        grid[py][px]='•'
        if not i: continue
        ax,ay=points[i-1]
        steps=max(abs(px-ax),abs(py-ay))
        for step in range(1,steps):
            gx=round(ax+(px-ax)*step/steps);gy=round(ay+(py-ay)*step/steps)
            grid[gy][gx]='─' if py==ay else ('╱' if py<ay else '╲')
    output=[]
    for i,line in enumerate(grid):
        label=f'{high-(high-low)*i/(h-1):.2f}' if i in (0,h//2,h-1) else ''
        output.append(f'{label:>9} │'+''.join(line))
    output.append('          └'+'─'*w)
    ticks=[' ']*w
    for i in sorted({0,len(rows)//2,len(rows)-1}):
        label=date_label(rows[i]['timestamp'])[:6]
        pos=max(0,min(w-len(label),x(i)-len(label)//2))
        ticks[pos:pos+len(label)]=label
    output.append('           '+''.join(ticks))
    marks=[' ']*w
    for i,r in enumerate(rows):
        if any(t==r['timestamp'] or (state.zooms[state.level][1]=='day' and hk_date(t)==hk_date(r['timestamp'])) for t in annotations):
            marks[x(i)]='●'
    marks[x(state.index-start)]='▲'
    output.append(('> ' if state.row==0 else '  ')+'         '+''.join(marks))
    output.append('           '+date_label(state.selected['timestamp'],state.zooms[state.level][1]!='day'))
    return '\n'.join(output)


class Body(VerticalScroll):
    can_focus = False


class PriceApp(App):
    BINDINGS = [Binding("escape", "back", priority=True, show=False)]
    AUTO_FOCUS = ""
    ENABLE_COMMAND_PALETTE = False
    CSS = '''
    Screen { background: #111111; color: #dddddd; }
    VerticalScroll { height: 1fr; padding: 1 1; scrollbar-size: 0 0; }
    Static { height: auto; }
    TextArea { height: auto; min-height: 3; max-height: 12; border: none; padding: 0; background: #111111; color: #dddddd; }
    TextArea:focus { border: none; }
    '''

    def __init__(self,ticker,metadata,observations,store,market,minute_available,notice=''):
        super().__init__()
        self.ticker=ticker;self.metadata=metadata;self.state=State(observations)
        self.daily=observations;self.store=store;self.market=market
        self.minute_available=minute_available;self.notice=notice
        if minute_available:
            period = minute_available if isinstance(minute_available,str) else '1m'
            minutes = {'1m':1,'5m':5,'15m':15,'30m':30,'1h':60}[period]
            self.state.zooms[5:]=[('1D',period,max(1,330//minutes)),('1H',period,max(1,60//minutes))]
        self.expanded=False;self.editing=False;self.anchor=None;self.loading=False

    def compose(self) -> ComposeResult:
        with Body():
            yield Static('STOCK · PRICE\n'+self.ticker+' · '+self.metadata['currency'],id='heading')
            yield Static(id='chart')
            yield Static(id='annotation')
            yield TextArea('',id='editor',soft_wrap=True,show_line_numbers=False,tab_behavior='indent')
            yield Static(id='zoom')
            yield Static(id='status')
            yield Static('↑↓ Row   ←→ Navigate   Space Expand   A Add   Esc Back',id='help')

    def on_mount(self):
        editor = self.query_one('#editor', TextArea)
        editor.register_theme(TextAreaTheme('mono',
            base_style=Style(color='#dddddd', bgcolor='#111111'),
            cursor_style=Style(color='#111111', bgcolor='#dddddd'),
            cursor_line_style=Style(bgcolor='#111111'),
            selection_style=Style(color='#ffffff', bgcolor='#444444')))
        editor.theme='mono'
        self.query_one('#editor').display=False
        self.query_one('#editor').disabled=True
        self.set_focus(None)
        self.paint()

    def on_resize(self):
        if self.is_mounted: self.paint()

    def timestamp(self):
        return self.anchor or self.state.selected['timestamp']

    def paint(self):
        if not self.is_mounted: return
        annotations=self.store.annotations(self.ticker)
        self.query_one('#chart',Static).update(Text(chart(self.state,annotations,self.size.width-3,max(5,min(16,self.size.height-15)))))
        timestamp=self.timestamp();text=annotations.get(timestamp,'')
        prefix='> ' if self.state.row==1 else '  '
        content=text if self.expanded else (text.splitlines()[0] if text else 'No annotation')
        if not self.expanded and len(content)>max(20,self.size.width-24):
            content=content[:max(20,self.size.width-27)]+'...'
        wrapped=textwrap.fill(content,width=max(20,self.size.width-6),replace_whitespace=False) if self.expanded else content
        self.query_one('#annotation',Static).update(Text(prefix+date_label(timestamp)+' · '+wrapped))
        self.query_one('#annotation').display=not self.editing
        z=self.state.level;maximum=6 if self.minute_available else 4
        prev=self.state.zooms[z-1][0] if z else '—';nxt=self.state.zooms[z+1][0] if z<maximum else '—'
        selected=self.state.row==2
        zoom=f"{prev}{'←' if selected and z else ''}        {self.state.zooms[z][0]}        {'→' if selected and z<maximum else ''}{nxt}"
        self.query_one('#zoom',Static).update(('> ' if selected else '  ')+zoom)
        status='RAW · '+self.state.zooms[z][1]+' · observation spacing · HKT · HKEX'
        calendar=self.metadata.get('calendar',{})
        day=str(hk_date(self.state.selected['timestamp']))
        if day in calendar.get('half_trading_days',[]): status+=' · half day'
        elif day in calendar.get('trading_days',[]): status+=' · trading day'
        if self.loading: status+=' · loading'
        if self.notice: status+='\n'+self.notice
        if self.market and self.market.notices: status+='\n'+' · '.join(sorted(self.market.notices))
        self.query_one('#status',Static).update(Text(status))
        self.query_one('#help',Static).update('EDIT · Arrows Cursor   Space Insert   Esc Save' if self.editing else '↑↓ Row   ←→ Navigate   Space Expand   A Add   Esc Back')

    def begin_edit(self,adding=False):
        self.state.row=1;self.expanded=True;self.editing=True
        timestamp=self.timestamp()
        text=self.store.annotations(self.ticker).get(timestamp,'')
        if adding: self.store.annotate(self.ticker,timestamp,text)
        editor=self.query_one('#editor',TextArea)
        editor.disabled=False;editor.load_text(text);editor.display=True;editor.focus()
        editor.move_cursor(editor.document.end)
        self.paint();editor.scroll_visible()

    def save_edit(self):
        editor=self.query_one('#editor',TextArea)
        self.store.annotate(self.ticker,self.timestamp(),editor.text)
        self.editing=False;editor.display=False;editor.disabled=True;self.set_focus(None);self.paint()

    async def change_zoom(self,direction):
        old=self.state.level;new=max(0,min(6 if self.minute_available else 4,old+direction))
        if new==old: return
        anchor=self.timestamp()
        if self.state.zooms[old][1] != self.state.zooms[new][1]:
            self.loading=True;self.paint()
            try:
                data=self.daily if new<=4 else await asyncio.to_thread(self.market.history,self.ticker,self.state.zooms[new][1],anchor)
                # Preserve the historical instant even when its finer observation is unavailable.
                exact=next((i for i,r in enumerate(data) if r['timestamp']==anchor),None)
                if exact is None:
                    same=[i for i,r in enumerate(data) if hk_date(r['timestamp'])==hk_date(anchor)]
                    if not same: raise DataError('No observations at selected date; zoom unchanged')
                    target=datetime.fromisoformat(anchor.replace('Z','+00:00'))
                    exact=min(same,key=lambda i:abs((datetime.fromisoformat(data[i]['timestamp'].replace('Z','+00:00'))-target).total_seconds()))
                self.state.observations=data;self.state.index=exact;self.anchor=anchor
            except DataError as e:
                self.notice=str(e);return
            finally:
                self.loading=False
        self.state.level=new;self.paint()

    def action_back(self):
        if self.editing:
            self.save_edit()
        else:
            self.exit()

    async def on_key(self,event):
        if self.editing:
            if event.key=='escape':
                event.stop();event.prevent_default();self.save_edit()
            return
        event.stop();event.prevent_default()
        if self.loading: return
        if event.key=='escape': self.exit();return
        if event.key in ('up','down'):
            self.state.select_row(-1 if event.key=='up' else 1)
        elif event.key in ('a','A'):
            self.begin_edit(adding=True);return
        elif event.key=='space' and self.state.row==1:
            self.expanded=not self.expanded
        elif event.key in ('left','right'):
            direction=-1 if event.key=='left' else 1
            if self.state.row==0:
                self.state.move(direction);self.anchor=None;self.expanded=False
            elif self.state.row==2:
                await self.change_zoom(direction)
            elif direction>0:
                if self.expanded: self.begin_edit();return
                self.expanded=True
            else: self.expanded=False
        self.paint()
        self.query_one(['#chart','#annotation','#zoom'][self.state.row]).scroll_visible()
