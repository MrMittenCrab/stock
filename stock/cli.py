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
    args=parser.parse_args()
    if args.command=='archive' and args.metadata and args.file:
        parser.error('Use either a document or --metadata')
    if args.command in ('price','archive'):
        try: args.ticker=symbol(args.ticker)
        except ValueError as e: parser.error(str(e))
    elif not args.name.strip():
        parser.error('Search name must not be empty')
    market=None
    store=None
    try:
        store=Store()
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
