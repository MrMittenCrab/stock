"""Compact monochrome price view with a shared timestamp scale."""
import asyncio
import textwrap
from bisect import bisect_right
from datetime import datetime
from rich.text import Text
from rich.style import Style
from textual.widgets.text_area import TextAreaTheme
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Static, TextArea
from .core import State
from .data import DataError, HK
from .exchanges import exchange


def date_label(timestamp, minute=False, timezone=HK):
    date = datetime.fromisoformat(timestamp.replace('Z','+00:00')).astimezone(timezone)
    return date.strftime('%d %b %Y' + (' %H:%M %Z' if minute else '')).upper()


ORIGIN = 11


def chart(state, annotations, width, height, venue=None):
    venue = venue or exchange('700.HK')
    rows, start = state.window()
    w, h = max(1, width-ORIGIN), max(2, height)
    values = [float(r['close']) for r in rows]
    low, high = min(values), max(values)
    if low == high:
        low -= max(abs(low)*0.001, 0.01)
        high += max(abs(high)*0.001, 0.01)
    times = [datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00')).timestamp() for r in rows]
    def x(i):
        return round((times[i]-times[0]) / (times[-1]-times[0] or 1) * (w-1))
    def y(value):
        return round((high-value)/(high-low)*(h-1))

    # Join cell edges, including endpoints: one connected stroke, no point glyphs.
    ports = {}
    def join(a, b):
        dx, dy = b[0]-a[0], b[1]-a[1]
        ports.setdefault(a, set()).add((dx, dy))
        ports.setdefault(b, set()).add((-dx, -dy))
    # Sample the piecewise linear price path once per terminal column. Several
    # observations may share a cell when zoomed out; drawing each independently
    # produces retraced vertical strokes and dangling branches.
    points = [(0, y(values[0]))]
    if len(rows) > 1:
        for column in range(1, w):
            instant = times[0]+(times[-1]-times[0])*column/max(1,w-1)
            right = min(len(rows)-1, bisect_right(times, instant))
            left = right-1
            fraction = (instant-times[left])/(times[right]-times[left] or 1)
            value = values[left]+(values[right]-values[left])*fraction
            points.append((column, y(value)))
    ports[points[0]] = set()
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        join((ax, ay), (bx, ay))
        cy = ay
        while cy != by:
            step = 1 if by > cy else -1
            join((bx, cy), (bx, cy+step));cy += step
    glyphs = {frozenset(d): c for d, c in [
        ([(-1,0),(1,0)], '─'), ([(0,-1),(0,1)], '│'),
        ([(1,0),(0,1)], '╭'), ([(-1,0),(0,1)], '╮'),
        ([(1,0),(0,-1)], '╰'), ([(-1,0),(0,-1)], '╯')]}
    grid = [[' ']*w for _ in range(h)]
    for (px, py), directions in ports.items():
        grid[py][px] = glyphs.get(frozenset(directions),
                                  '│' if directions and all(dx == 0 for dx,dy in directions) else '─')
    output = []
    for i, line in enumerate(grid):
        label = f'{high-(high-low)*i/(h-1):.2f}' if i in (0,h//2,h-1) else ''
        output.append(f'{label:>9} │'+''.join(line))
    marks = [' ']*w
    for i, row in enumerate(rows):
        if any(t == row['timestamp'] or
               (state.zooms[state.level][1] == 'day' and venue.date(t) == venue.date(row['timestamp']))
               for t in annotations):
            marks[x(i)] = '●'
    marks[x(state.index-start)] = '▼'
    output.append(('> ' if state.row == 0 else '  ')+' '*(ORIGIN-2)+''.join(marks))
    output.append(' '*(ORIGIN-1)+'└'+'─'*w)
    ticks = [' ']*w
    occupied = set()
    for i in dict.fromkeys([len(rows)-1, 0, len(rows)//4, len(rows)//2, 3*len(rows)//4]):
        label = date_label(rows[i]['timestamp'], timezone=venue.timezone) if i == len(rows)-1 else date_label(rows[i]['timestamp'], timezone=venue.timezone)[:2]
        if len(label) > w: label = label[:2]
        pos = max(0, min(w-len(label), x(i)-len(label)//2))
        cells = set(range(pos, pos+len(label)))
        if not cells & occupied:
            ticks[pos:pos+len(label)] = label
            occupied.update(range(max(0,pos-1), min(w,pos+len(label)+1)))
    output.append(' '*ORIGIN+''.join(ticks))
    return '\n'.join(output)


class Body(VerticalScroll):
    can_focus = False


class PriceApp(App):
    BINDINGS = [Binding("escape", "back", priority=True, show=False),
                Binding("up", "row(-1)", priority=True, show=False),
                Binding("down", "row(1)", priority=True, show=False)]
    AUTO_FOCUS = ""
    ENABLE_COMMAND_PALETTE = False
    CSS = '''
    Screen { background: #111111; color: #dddddd; }
    VerticalScroll { height: 1fr; padding: 1 1; scrollbar-size: 0 0; }
    Static { height: auto; }
    TextArea { height: auto; min-height: 1; border: none; padding: 0; background: #111111; color: #dddddd; }
    TextArea:focus { border: none; }
    TextArea { margin-left: 11; }
    #heading { margin-bottom: 1; }
    '''

    def __init__(self,ticker,metadata,observations,store,market,minute_available,notice=''):
        super().__init__()
        self.venue=exchange(ticker)
        self.ticker=ticker;self.metadata=metadata;self.state=State(observations)
        self.minimum_level=next((i for i,(_,_,count) in enumerate(self.state.zooms[:5]) if count<=len(observations)),4)
        self.state.level=max(self.minimum_level,self.state.level)
        self.daily=observations;self.store=store;self.market=market
        self.minute_available=minute_available;self.notice=notice
        if minute_available:
            period = minute_available if isinstance(minute_available,str) else '1m'
            minutes = {'1m':1,'5m':5,'15m':15,'30m':30,'1h':60}[period]
            self.state.zooms[5:]=[('1D',period,max(1,self.venue.session_minutes//minutes)),('1H',period,max(1,60//minutes))]
        self.expanded=False;self.editing=False;self.anchor=None;self.loading=False

    def compose(self) -> ComposeResult:
        with Body():
            yield Static('STOCK · PRICE\n'+self.ticker+' · '+self.metadata['currency'],id='heading')
            yield Static(id='chart')
            yield Static(id='annotation')
            yield TextArea('',id='editor',soft_wrap=True,show_line_numbers=False,tab_behavior='indent')
            yield Static(id='zoom')
            yield Static(id='status')
            yield Static('↑↓ Row   ←→ Navigate   Space Expand   A Add   Esc Quit',id='help')

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
        if self.is_mounted: self.call_after_refresh(self.paint)

    def timestamp(self):
        return self.anchor or self.state.selected['timestamp']

    def paint(self):
        if not self.is_mounted: return
        annotations=self.store.annotations(self.ticker)
        self.query_one('#chart',Static).update(Text(chart(self.state,annotations,self.size.width-2,max(4,min(16,self.size.height-11)),self.venue)))
        timestamp=self.timestamp();text=annotations.get(timestamp,'')
        prefix='> ' if self.state.row==1 else '  '
        content=text if self.expanded else (text.splitlines()[0] if text else 'No annotation')
        if not self.expanded and len(content)>max(20,self.size.width-24):
            content=content[:max(20,self.size.width-27)]+'...'
        content = date_label(timestamp, self.state.zooms[self.state.level][1]!='day',self.venue.timezone)+(' · '+content if not self.editing else '')
        available = max(1, self.size.width-2-ORIGIN)
        lines = []
        for paragraph in content.split('\n'):
            lines.extend(textwrap.wrap(paragraph, width=available, replace_whitespace=False) or [''])
        aligned = '\n'.join((' '*ORIGIN)+line for line in lines)
        aligned = prefix+aligned[2:]
        self.query_one('#annotation',Static).update(Text(aligned))
        self.query_one('#annotation').display=True
        z=self.state.level;maximum=6 if self.minute_available else 4
        prev=self.state.zooms[z-1][0] if z>self.minimum_level else '—';nxt=self.state.zooms[z+1][0] if z<maximum else '—'
        selected=self.state.row==2
        current=self.state.zooms[z][0]
        gap=' '*max(1,min(8,(self.size.width-2-ORIGIN-len(prev)-len(current)-len(nxt)-2)//2))
        zoom=f"{prev}←{gap}{current}{gap}→{nxt}"
        self.query_one('#zoom',Static).update(Text(('> ' if selected else '  ')+' '*(ORIGIN-2)+zoom))
        notices = [self.notice] if self.notice else []
        if self.loading: notices.append('Loading…')
        if self.market and self.market.notices: notices.extend(sorted(self.market.notices))
        self.query_one('#status',Static).update(Text('\n'.join(notices)))
        self.query_one('#status').display = bool(notices)
        self.query_one('#help',Static).update('↑↓ Save / Row   ←→ Caret   Space Insert   Esc Quit' if self.editing else '↑↓ Row   ←→ Navigate   Space Expand   A Add   Esc Quit')

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
        old=self.state.level;new=max(self.minimum_level,min(6 if self.minute_available else 4,old+direction))
        if new==old: return
        anchor=self.timestamp()
        if self.state.zooms[old][1] != self.state.zooms[new][1]:
            self.loading=True;self.paint()
            try:
                data=self.daily if new<=4 else await asyncio.to_thread(self.market.history,self.ticker,self.state.zooms[new][1],anchor)
                # Preserve the historical instant even when its finer observation is unavailable.
                exact=next((i for i,r in enumerate(data) if r['timestamp']==anchor),None)
                if exact is None:
                    same=[i for i,r in enumerate(data) if self.venue.date(r['timestamp'])==self.venue.date(anchor)]
                    if not same: raise DataError('No observations at selected date; zoom unchanged')
                    target=datetime.fromisoformat(anchor.replace('Z','+00:00'))
                    exact=min(same,key=lambda i:abs((datetime.fromisoformat(data[i]['timestamp'].replace('Z','+00:00'))-target).total_seconds()))
                self.state.observations=data;self.state.index=exact;self.anchor=anchor
            except DataError as e:
                self.notice=str(e);return
            finally:
                self.loading=False
                self.paint()
        self.state.level=new;self.paint()

    def action_back(self):
        if self.editing:
            self.save_edit()
        self.exit()

    def action_row(self, direction):
        if self.loading: return
        if self.editing:
            self.save_edit()
        self.state.select_row(direction)
        self.paint()
        self.query_one(['#chart','#annotation','#zoom'][self.state.row]).scroll_visible()

    async def on_key(self,event):
        if self.editing:
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
