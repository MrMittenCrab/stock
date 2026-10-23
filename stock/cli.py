import argparse
import sys
import sqlite3
from .core import Store, symbol
from .data import Market, DataError


def main():
    parser=argparse.ArgumentParser(prog='stock',description='US and Hong Kong equities · keyboard terminal')
    commands=parser.add_subparsers(dest='command',required=True)
    price=commands.add_parser('price',help='Open historical price terminal')
    price.add_argument('ticker')
    search=commands.add_parser('search',help='Find US and HK securities by name or symbol')
    search.add_argument('name')
    archive=commands.add_parser('archive',help='Browse or import archived research documents')
    archive.add_argument('ticker')
    archive.add_argument('file',nargs='?')
    archive.add_argument('--metadata',metavar='JSON',help='Enrich existing archived documents from versioned metadata JSON')
    sort=commands.add_parser('sort',help='Build distinct, verified investment insights from archived sources')
    sort.add_argument('ticker')
    sort.add_argument('--rebuild',metavar='DOCUMENT',help='Stage and review replacement evidence for one document')
    sort.add_argument('--insights',action='store_true',help=argparse.SUPPRESS)
    sort.add_argument('--review-only',action='store_true',help='Preview insights without publishing evidence or activating groups')
    sort.add_argument('--reset',metavar='DOCUMENT',help='Restore frozen topics by Archive ID or filename; no LLM call')
    sort.add_argument('--document-seconds',type=float,default=720,help='Per-document wall-clock budget (default: 720)')
    sort.add_argument('--command-seconds',type=float,default=1200,help='Command wall-clock budget (default: 1200)')
    sort.add_argument('--cursor-requests',type=int,default=12,help='Cursor requests per document (default: 12)')
    sort.add_argument('--request-seconds',type=float,default=120,help='Request timeout (default: 120)')
    sources=commands.add_parser('sources',help='Browse source passages and edit topic memberships')
    sources.add_argument('ticker')
    args=parser.parse_args()
    if args.command=='archive' and args.metadata and args.file:
        parser.error('Use either a document or --metadata')
    if args.command in ('price','archive','sort','sources'):
        try: args.ticker=symbol(args.ticker)
        except ValueError as e: parser.error(str(e))
    elif not args.name.strip():
        parser.error('Search name must not be empty')
    market=None
    store=None
    try:
        store=Store()
        if args.command=='sort':
            if args.reset and (args.rebuild or args.review_only):raise ValueError('Use --reset separately')
            if args.rebuild and args.review_only:raise ValueError('Use --review-only separately from --rebuild')
            if args.reset:
                from .sources import reset
                doc=reset(store,args.ticker,args.reset)
                print(f"{doc['id']} · Restored frozen topics")
                return 0
            from .sort import sort_stock,Cursor
            from .sort_process import Status
            from .sort_budget import Budget,BudgetExceeded
            import time
            with Budget(args.document_seconds,args.command_seconds,args.cursor_requests,args.request_seconds):
                with Status() as status:
                    try:
                        if args.rebuild:
                            from .rebuild import rebuild
                            ok=rebuild(store,args.ticker,args.rebuild,Cursor,status,status.approval)
                        else:ok=sort_stock(store,args.ticker,status,review_only=args.review_only)
                    except BudgetExceeded as exc:
                        elapsed=int(time.monotonic()-status.started)
                        status.review(f"{status.document or args.ticker} · Paused · {exc} · {elapsed//60:02}:{elapsed%60:02}")
                        resume=f"stock sort {args.ticker}"+(f" --rebuild {args.rebuild}" if args.rebuild else ' --review-only' if args.review_only else '')
                        status.review(f'Resume · {resume} · Log · {status.log_path}')
                        return 1
                    from .insights import entries
                    from .sources import passages
                    insight_count,source_count=status.preview_counts or (len(entries(store,args.ticker)),len(passages(store,args.ticker)))
                    elapsed=int(time.monotonic()-status.started)
                    status.review(f"{args.ticker} · {'Preview' if args.review_only else 'Done' if ok else 'Paused'} · {insight_count} insights · {source_count} sources · {elapsed//60:02}:{elapsed%60:02}")
                    return 0 if ok else 1
        if args.command=='sources':
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise ValueError('stock sources requires an interactive terminal')
            from .sources_ui import SourcesApp
            SourcesApp(args.ticker,store).run(mouse=False)
            return 0
        if args.command=='archive':
            if args.metadata:
                from .archive import import_metadata
                count=import_metadata(store,args.ticker,args.metadata)
                print(f'Enriched {count} documents')
            elif args.file:
                from .archive import import_document
                doc=import_document(store,args.ticker,args.file)
                from pathlib import Path
                print('Archived  '+Path(doc['original']).name)
                if doc['conversion_status']=='converted':
                    print('Converted '+Path(doc['markdown']).name)
                elif doc['conversion_status']=='failed':
                    print('stock: PDF archived; '+doc['conversion_error']+'; reimport to retry conversion',file=sys.stderr)
                    return 1
            else:
                if not sys.stdin.isatty() or not sys.stdout.isatty():
                    raise ValueError('stock archive requires an interactive terminal; provide a file to import')
                from .archive_ui import ArchiveApp
                ArchiveApp(args.ticker,store).run(mouse=False)
            return 0
        market=Market(store)
        if args.command=='search':
            matches=market.search(args.name)
            for ticker,name in matches: print(f'{ticker:<12} · {name} · {ticker.rsplit(".",1)[1]}')
            if not matches: print('No matching US or HK securities')
            for notice in market.notices: print(notice,file=sys.stderr)
        else:
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise DataError('stock price requires an interactive terminal')
            print('Loading Longbridge history…',file=sys.stderr)
            metadata=market.metadata(args.ticker)
            rows=market.history(args.ticker)
            notices=[]
            try: metadata["calendar"] = market.calendar(rows[-21:],args.ticker)
            except DataError as e: notices.append(f'Calendar unavailable · {e}')
            minute=False
            try:
                minute=market.finest(args.ticker)
            except DataError as e:
                notices.append(f'Intraday unavailable · {e}')
            from .ui import PriceApp
            PriceApp(args.ticker,metadata,rows,store,market,minute,'\n'.join(notices)).run(mouse=False)
    except (DataError,OSError,ValueError,sqlite3.Error) as e:
        print(f'stock: {e}',file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    finally:
        if market: market.rpc.close()
        if store: store.db.close()
    return 0
