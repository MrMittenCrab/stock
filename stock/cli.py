import argparse
import sys
import sqlite3
from .core import Store, symbol
from .data import Market, DataError


def main():
    parser=argparse.ArgumentParser(prog='stock',description='Hong Kong equities · keyboard terminal')
    commands=parser.add_subparsers(dest='command',required=True)
    price=commands.add_parser('price',help='Open historical price terminal')
    price.add_argument('ticker')
    search=commands.add_parser('search',help='Find HK securities by name or symbol')
    search.add_argument('name')
    args=parser.parse_args()
    if args.command=='price':
        try: args.ticker=symbol(args.ticker)
        except ValueError as e: parser.error(str(e))
    elif not args.name.strip():
        parser.error('Search name must not be empty')
    market=None
    try:
        store=Store();market=Market(store)
        if args.command=='search':
            matches=market.search(args.name)
            for ticker,name in matches: print(f'{ticker:<10} · {name}')
            if not matches: print('No matching HK securities')
            for notice in market.notices: print(notice,file=sys.stderr)
        else:
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise DataError('stock price requires an interactive terminal')
            print('Loading Longbridge history…',file=sys.stderr)
            metadata=market.metadata(args.ticker)
            rows=market.history(args.ticker)
            notices=[]
            try: metadata["calendar"] = market.calendar(rows[-21:])
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
    return 0
