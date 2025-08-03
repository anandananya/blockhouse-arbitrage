# cli.py
from __future__ import annotations
import argparse
import asyncio
import json
from typing import List

from xetrade.models import Pair, OrderRequest, OrderStatus
from xetrade.services.aggregator import best_across_venues
from xetrade.services.price_impact import price_impact_pct, walk_book
from xetrade.services.trading import UnifiedTradingService
from xetrade.services.position_monitor import PositionMonitorService
from xetrade.utils.symbol_mapper import UniversalSymbolMapper
from xetrade.exchanges.base import make_exchanges, available_exchanges
from xetrade.exchanges import binance  # noqa: F401  # ensure registry side-effect

async def cmd_best(args):
    pair = Pair.parse(args.pair)
    exchanges = make_exchanges(args.venues.split(","))
    
    try:
        result = await best_across_venues(exchanges, pair)
        # JSON for easy reading/piping
        def simplify(vq):
            return None if vq is None else {"venue": vq["venue"], "price": vq["price"], "ts_ms": vq["ts_ms"]}
        out = {
            "pair": pair.human(),
            "best_bid": simplify(result["best_bid"]),
            "best_ask": simplify(result["best_ask"]),
            "mid": result["mid"],
            "venues_queried": len(exchanges),
            "venues_with_data": len(result.get("all", [])),
        }
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "pair": pair.human(),
            "venues_queried": len(exchanges),
        }, indent=2))
        return 1
    return 0

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
    
    try:
        if not ex.supports_funding:
            print(json.dumps({
                "error": f"{ex.name} does not support funding rates",
                "venue": ex.name,
                "pair": pair.human(),
                "supports_funding": False,
            }, indent=2))
            return 1
            
        snap = await ex.get_funding_live_predicted(pair)
        print(json.dumps({
            "venue": ex.name,
            "pair": pair.human(),
            "current_rate": snap.current_rate,
            "predicted_next_rate": snap.predicted_next_rate,
            "interval_hours": snap.interval_hours,
            "ts_ms": snap.ts_ms,
            "supports_funding": True,
        }, indent=2))
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "venue": ex.name,
            "pair": pair.human(),
            "supports_funding": ex.supports_funding,
        }, indent=2))
        return 1
    return 0

async def cmd_place_order(args):
    """Place an order on a specific venue."""
    pair = Pair.parse(args.pair)
    exchanges = make_exchanges([args.venue])
    trading_service = UnifiedTradingService(exchanges)
    
    # Validate price for LIMIT orders
    if args.order_type == "LIMIT" and args.price is None:
        print(json.dumps({
            "error": "Price is required for LIMIT orders",
            "pair": pair.human(),
            "venue": args.venue,
        }, indent=2))
        return 1
    
    request = OrderRequest(
        pair=pair,
        side=args.side,
        order_type=args.order_type,
        quantity=args.quantity,
        price=args.price,
    )
    
    try:
        result = await trading_service.place_order(request, args.venue)
        print(json.dumps({
            "success": result.success,
            "venue": result.venue,
            "order_id": result.order_id,
            "error": result.error,
            "latency_ms": result.latency_ms,
            "pair": pair.human(),
            "side": args.side,
            "order_type": args.order_type,
            "quantity": args.quantity,
            "price": args.price,
        }, indent=2))
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "pair": pair.human(),
            "venue": args.venue,
        }, indent=2))
        return 1
    return 0

async def cmd_cancel_order(args):
    """Cancel an order on a specific venue."""
    pair = Pair.parse(args.pair)
    exchanges = make_exchanges([args.venue])
    trading_service = UnifiedTradingService(exchanges)
    
    try:
        result = await trading_service.cancel_order(args.order_id, pair, args.venue)
        print(json.dumps({
            "success": result.success,
            "venue": result.venue,
            "order_id": args.order_id,
            "error": result.error,
            "latency_ms": result.latency_ms,
            "pair": pair.human(),
        }, indent=2))
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "pair": pair.human(),
            "venue": args.venue,
            "order_id": args.order_id,
        }, indent=2))
        return 1
    return 0

async def cmd_order_status(args):
    """Get the status of an order."""
    pair = Pair.parse(args.pair)
    exchanges = make_exchanges([args.venue])
    trading_service = UnifiedTradingService(exchanges)
    
    try:
        status = await trading_service.get_order_status(args.order_id, pair, args.venue)
        if status:
            print(json.dumps({
                "order_id": status.order_id,
                "venue": status.venue,
                "pair": status.pair.human(),
                "side": status.side,
                "order_type": status.order_type,
                "quantity": status.quantity,
                "filled_quantity": status.filled_quantity,
                "price": status.price,
                "avg_fill_price": status.avg_fill_price,
                "status": status.status.value,
                "ts_ms": status.ts_ms,
            }, indent=2))
        else:
            print(json.dumps({
                "error": "Order not found or venue not supported",
                "order_id": args.order_id,
                "venue": args.venue,
                "pair": pair.human(),
            }, indent=2))
            return 1
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "order_id": args.order_id,
            "venue": args.venue,
            "pair": pair.human(),
        }, indent=2))
        return 1
    return 0

async def cmd_position(args):
    """Get position details from a filled order."""
    pair = Pair.parse(args.pair)
    exchanges = make_exchanges([args.venue])
    position_service = PositionMonitorService(exchanges)
    
    try:
        summary = await position_service.get_position_summary(args.order_id, pair, args.venue)
        print(json.dumps(summary, indent=2))
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "order_id": args.order_id,
            "venue": args.venue,
            "pair": pair.human(),
        }, indent=2))
        return 1
    return 0

async def cmd_monitor(args):
    """Monitor a position live with periodic updates."""
    pair = Pair.parse(args.pair)
    exchanges = make_exchanges([args.venue])
    position_service = PositionMonitorService(exchanges)
    
    print(f"🔍 Monitoring position for order {args.order_id}")
    print(f"📊 Venue: {args.venue}, Pair: {pair.human()}")
    print(f"⏱️  Update interval: {args.interval}s, Max updates: {args.max_updates}")
    print("=" * 60)
    
    try:
        results = await position_service.monitor_position_live(
            args.order_id, pair, args.venue, 
            args.interval, args.max_updates
        )
        
        for i, result in enumerate(results, 1):
            print(f"\n📈 Update {i}/{len(results)}:")
            if result.success and result.position and result.pnl:
                position = result.position
                pnl = result.pnl
                
                # Format timestamp
                import datetime
                entry_time = datetime.datetime.fromtimestamp(position.entry_timestamp / 1000)
                pnl_time = datetime.datetime.fromtimestamp(pnl.ts_ms / 1000)
                
                print(f"   🏢 Venue: {position.venue}")
                print(f"   📊 Pair: {position.pair.human()}")
                print(f"   📅 Entry Time: {entry_time}")
                print(f"   💰 Entry Price: ${position.entry_price:,.2f}")
                print(f"   📏 Quantity: {position.quantity}")
                print(f"   📈 Position Side: {position.position_side.upper()}")
                print(f"   💵 Current Price: ${pnl.current_price:,.2f}")
                print(f"   📊 Mark Price: ${pnl.mark_price:,.2f}")
                print(f"   💸 Unrealized PnL: ${pnl.unrealized_pnl:,.2f} ({pnl.unrealized_pnl_pct:+.2f}%)")
                print(f"   🎯 Status: {'🟢 PROFIT' if pnl.is_profitable else '🔴 LOSS' if pnl.unrealized_pnl < 0 else '⚪ BREAKEVEN'}")
                print(f"   ⏱️  Latency: {result.latency_ms:.2f}ms")
                print(f"   🕐 PnL Time: {pnl_time}")
            else:
                print(f"   ❌ Error: {result.error}")
                print(f"   ⏱️  Latency: {result.latency_ms:.2f}ms")
        
        print(f"\n✅ Monitoring completed. Total updates: {len(results)}")
        
    except Exception as e:
        print(f"❌ Monitoring error: {e}")
        return 1
    return 0

async def cmd_map_symbol(args):
    """Map exchange symbol to universal format."""
    mapper = UniversalSymbolMapper()
    
    try:
        mapping = mapper.map_symbol(args.symbol, args.exchange)
        print(json.dumps({
            "exchange_symbol": mapping.exchange_symbol,
            "universal_symbol": mapping.universal_symbol,
            "base_asset": mapping.base_asset,
            "quote_asset": mapping.quote_asset,
            "quote_type": mapping.quote_type.value,
            "confidence": mapping.confidence,
            "exchange": args.exchange
        }, indent=2))
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "symbol": args.symbol,
            "exchange": args.exchange
        }, indent=2))
        return 1
    return 0

async def cmd_universal_to_exchange(args):
    """Convert universal symbol to exchange format."""
    mapper = UniversalSymbolMapper()
    
    try:
        exchange_symbol = mapper.get_exchange_symbol(args.symbol, args.exchange)
        print(json.dumps({
            "universal_symbol": args.symbol,
            "exchange_symbol": exchange_symbol,
            "exchange": args.exchange
        }, indent=2))
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "universal_symbol": args.symbol,
            "exchange": args.exchange
        }, indent=2))
        return 1
    return 0

async def cmd_validate_mapping(args):
    """Validate symbol mapping."""
    mapper = UniversalSymbolMapper()
    
    try:
        is_valid = mapper.validate_mapping(args.exchange_symbol, args.expected_universal, args.exchange)
        print(json.dumps({
            "exchange_symbol": args.exchange_symbol,
            "expected_universal": args.expected_universal,
            "actual_universal": mapper.normalize_symbol(args.exchange_symbol, args.exchange),
            "is_valid": is_valid,
            "exchange": args.exchange
        }, indent=2))
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "exchange_symbol": args.exchange_symbol,
            "expected_universal": args.expected_universal,
            "exchange": args.exchange
        }, indent=2))
        return 1
    return 0

async def cmd_demo_mapper(args):
    """Demonstrate symbol mapper with examples."""
    mapper = UniversalSymbolMapper()
    
    print("🎯 Universal Symbol Mapper Demo")
    print("=" * 50)
    
    # Test cases from the requirements
    test_cases = [
        ("1000BONK-USD", "derive"),
        ("BONK-USDT", "binance"),
        ("BTCUSDT", "binance"),
        ("BTC-USDT", "okx"),
        ("BTC_USDT", "bitmart"),
        ("ETH-USD", "derive"),
        ("100SHIB-USDT", "kucoin"),
        ("DOGE-USDT", "binance"),
        ("SOL-USD", "derive"),
        ("XBT-USDT", "okx"),  # XBT is sometimes used for Bitcoin
    ]
    
    print("📊 Symbol Mapping Examples:")
    print("-" * 30)
    
    for exchange_symbol, exchange in test_cases:
        mapping = mapper.map_symbol(exchange_symbol, exchange)
        print(f"🔗 {exchange_symbol} ({exchange}) → {mapping.universal_symbol}")
        print(f"   Base: {mapping.base_asset}, Quote: {mapping.quote_asset}")
        print(f"   Quote Type: {mapping.quote_type.value}, Confidence: {mapping.confidence:.2f}")
        print()
    
    # Demonstrate reverse mapping
    print("🔄 Reverse Mapping Examples:")
    print("-" * 30)
    
    universal_symbols = ["BONK/USD", "BTC/USDT", "ETH/USD", "SOL/USDT"]
    exchanges = ["binance", "okx", "derive", "kucoin"]
    
    for universal_symbol in universal_symbols:
        print(f"📋 {universal_symbol}:")
        for exchange in exchanges:
            exchange_symbol = mapper.get_exchange_symbol(universal_symbol, exchange)
            print(f"   {exchange}: {exchange_symbol}")
        print()
    
    # Demonstrate quote currency classification
    print("💰 Quote Currency Classification:")
    print("-" * 30)
    
    quote_types = mapper.get_all_quote_types()
    for quote_type, currencies in quote_types.items():
        print(f"📊 {quote_type.value}: {', '.join(currencies)}")
    
    print(f"\n✅ Demo completed! The mapper handles:")
    print("   ✅ Prefix variations (1000BONK → BONK)")
    print("   ✅ Suffix variations (-USD vs -USDT)")
    print("   ✅ Separator variations (BTCUSDT vs BTC-USDT)")
    print("   ✅ Quote currency normalization")
    print("   ✅ Exchange-specific patterns")

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

    # trading commands
    p_place = sub.add_parser("place", help="Place an order")
    p_place.add_argument("--venue", required=True, help="e.g., okx")
    p_place.add_argument("--pair", required=True, help="e.g., BTC-USDT")
    p_place.add_argument("--side", choices=("buy", "sell"), required=True)
    p_place.add_argument("--order-type", choices=("LIMIT", "MARKET"), required=True)
    p_place.add_argument("--quantity", type=float, required=True, help="Base asset quantity")
    p_place.add_argument("--price", type=float, help="Price (required for LIMIT orders)")
    p_place.set_defaults(func=cmd_place_order)

    p_cancel = sub.add_parser("cancel", help="Cancel an order")
    p_cancel.add_argument("--venue", required=True, help="e.g., okx")
    p_cancel.add_argument("--pair", required=True, help="e.g., BTC-USDT")
    p_cancel.add_argument("--order-id", required=True, help="Order ID to cancel")
    p_cancel.set_defaults(func=cmd_cancel_order)

    p_status = sub.add_parser("status", help="Get order status")
    p_status.add_argument("--venue", required=True, help="e.g., okx")
    p_status.add_argument("--pair", required=True, help="e.g., BTC-USDT")
    p_status.add_argument("--order-id", required=True, help="Order ID to check")
    p_status.set_defaults(func=cmd_order_status)

    # position monitoring commands
    p_position = sub.add_parser("position", help="Get position details from filled order")
    p_position.add_argument("--venue", required=True, help="e.g., okx")
    p_position.add_argument("--pair", required=True, help="e.g., BTC-USDT")
    p_position.add_argument("--order-id", required=True, help="Order ID of filled order")
    p_position.set_defaults(func=cmd_position)

    p_monitor = sub.add_parser("monitor", help="Monitor position live with updates")
    p_monitor.add_argument("--venue", required=True, help="e.g., okx")
    p_monitor.add_argument("--pair", required=True, help="e.g., BTC-USDT")
    p_monitor.add_argument("--order-id", required=True, help="Order ID to monitor")
    p_monitor.add_argument("--interval", type=int, default=30, help="Update interval in seconds")
    p_monitor.add_argument("--max-updates", type=int, default=5, help="Maximum number of updates")
    p_monitor.set_defaults(func=cmd_monitor)

    # symbol mapping commands
    p_map = sub.add_parser("map", help="Map exchange symbol to universal format")
    p_map.add_argument("--symbol", required=True, help="Exchange-specific symbol (e.g., BTCUSDT)")
    p_map.add_argument("--exchange", required=True, help="Exchange name (e.g., binance)")
    p_map.set_defaults(func=cmd_map_symbol)

    p_universal = sub.add_parser("universal", help="Convert universal symbol to exchange format")
    p_universal.add_argument("--symbol", required=True, help="Universal symbol (e.g., BTC/USDT)")
    p_universal.add_argument("--exchange", required=True, help="Target exchange name")
    p_universal.set_defaults(func=cmd_universal_to_exchange)

    p_validate = sub.add_parser("validate", help="Validate symbol mapping")
    p_validate.add_argument("--exchange-symbol", required=True, help="Exchange-specific symbol")
    p_validate.add_argument("--expected-universal", required=True, help="Expected universal symbol")
    p_validate.add_argument("--exchange", required=True, help="Exchange name")
    p_validate.set_defaults(func=cmd_validate_mapping)

    p_demo = sub.add_parser("demo-mapper", help="Demonstrate symbol mapper with examples")
    p_demo.set_defaults(func=cmd_demo_mapper)

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

