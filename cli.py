# cli.py
from __future__ import annotations
import argparse
import asyncio
import json
from typing import List

from xetrade.models import Pair
from xetrade.services.aggregator import best_across_venues
from xetrade.services.price_impact import price_impact_pct, walk_book
from xetrade.exchanges.base import make_exchanges, available_exchanges
from xetrade.exchanges import binance  # noqa: F401  # ensure registry side-effect

async def cmd_best(args):
    pair = Pair.parse(args.pair)
    exchanges = make_exchanges(args.venues.split(","))
    result = await best_across_venues(exchanges, pair)
    # JSON for easy reading/piping
    def simplify(vq):
        return None if vq is None else {"venue": vq["venue"], "price": vq["price"], "ts_ms": vq["ts_ms"]}
    out = {
        "pair": pair.human(),
        "best_bid": simplify(result["best_bid"]),
        "best_ask": simplify(result["best_ask"]),
        "mid": result["mid"],
    }
    print(json.dumps(out, indent=2))

async def cmd_l2(args):
    pair = Pair.parse(args.pair)
    [ex] = make_exchanges([args.venue])
    ob = await ex.get_l2_orderbook(pair, depth=args.depth)
    print(json.dumps({
        "venue": ex.name,
        "pair": pair.human(),
        "ts_ms": ob.ts_ms,
        "best_bid": ob.best_bid(),
        "best_ask": ob.best_ask(),
        "bids_levels": len(ob.bids),
        "asks_levels": len(ob.asks),
    }, indent=2))

async def cmd_impact(args):
    pair = Pair.parse(args.pair)
    [ex] = make_exchanges([args.venue])
    ob = await ex.get_l2_orderbook(pair, depth=args.depth)
    avg_px, filled = walk_book(ob, args.side, args.quote)
    impact = price_impact_pct(ob, args.side, args.quote)
    print(json.dumps({
        "venue": ex.name,
        "pair": pair.human(),
        "side": args.side,
        "quote_spend": args.quote,
        "avg_execution_price": avg_px,
        "filled_base_qty": filled,
        "mid": ob.mid(),
        "price_impact_pct": impact,
    }, indent=2))

async def cmd_funding(args):
    pair = Pair.parse(args.pair)
    [ex] = make_exchanges([args.venue])
    snap = await ex.get_funding_live_predicted(pair)
    print(json.dumps({
        "venue": ex.name,
        "pair": pair.human(),
        "current_rate": snap.current_rate,
        "predicted_next_rate": snap.predicted_next_rate,
        "interval_hours": snap.interval_hours,
        "ts_ms": snap.ts_ms,
    }, indent=2))

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="xetrade", description="Simple crypto market CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    # best across venues
    p_best = sub.add_parser("best", help="Best bid/ask across venues")
    p_best.add_argument("--pair", required=True, help="e.g., BTC-USDT")
    p_best.add_argument("--venues", default="binance", help=f"comma list. known: {', '.join(available_exchanges()) or 'binance'}")
    p_best.set_defaults(func=cmd_best)

    # l2 book
    p_l2 = sub.add_parser("l2", help="Level-2 order book on a venue")
    p_l2.add_argument("--venue", required=True, help="e.g., binance")
    p_l2.add_argument("--pair", required=True, help="e.g., BTC-USDT")
    p_l2.add_argument("--depth", type=int, default=100)
    p_l2.set_defaults(func=cmd_l2)

    # price impact
    p_imp = sub.add_parser("impact", help="Simulate market order and report price impact")
    p_imp.add_argument("--venue", required=True)
    p_imp.add_argument("--pair", required=True)
    p_imp.add_argument("--side", choices=("buy", "sell"), required=True)
    p_imp.add_argument("--quote", type=float, required=True, help="Order size in quote currency, e.g., 50000")
    p_imp.add_argument("--depth", type=int, default=200)
    p_imp.set_defaults(func=cmd_impact)

    # funding
    p_fun = sub.add_parser("funding", help="Current & predicted funding on a venue")
    p_fun.add_argument("--venue", required=True)
    p_fun.add_argument("--pair", required=True)
    p_fun.set_defaults(func=cmd_funding)

    return p

# cli.py (replace main() with this version)
def main():
    parser = build_parser()
    args = parser.parse_args()

    async def _run():
        try:
            await args.func(args)
        finally:
            # always close the shared aiohttp session
            from xetrade.utils.http import http
            await http.close()

    asyncio.run(_run())

if __name__ == "__main__":
    main()

