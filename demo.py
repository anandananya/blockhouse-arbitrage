#!/usr/bin/env python3
"""
Demo script showcasing the cross-exchange trading engine functionality.
"""
import asyncio
import json
from xetrade.exchanges.base import make_exchanges, available_exchanges
from xetrade.models import Pair
from xetrade.services.aggregator import best_across_venues
from xetrade.services.price_impact import price_impact_pct, walk_book
from xetrade.services.funding import summarize_snapshot
from xetrade.utils.http import http

async def demo():
    print("🚀 Cross-Exchange Trading Engine Demo")
    print("=" * 50)
    
    # Initialize exchanges
    venues = ["okx", "kucoin", "bitmart", "derive"]
    exchanges = make_exchanges(venues)
    pair = Pair.parse("BTC-USDT")
    
    print(f"\n📊 Available exchanges: {', '.join(available_exchanges())}")
    print(f"🎯 Testing pair: {pair.human()}")
    print(f"🏢 Using venues: {', '.join(venues)}")
    
    # Show exchange capabilities
    print("\n🔧 Exchange Capabilities:")
    for ex in exchanges:
        funding_support = "✅" if ex.supports_funding else "❌"
        print(f"   {ex.name}: funding={funding_support}")
    
    try:
        # 1. Best bid/ask across venues
        print("\n1️⃣ Best Bid/Ask Across Venues")
        print("-" * 30)
        result = await best_across_venues(exchanges, pair)
        
        if result["best_bid"] and result["best_ask"]:
            print(f"✅ Best bid: {result['best_bid']['venue']} @ ${result['best_bid']['price']:,.2f}")
            print(f"✅ Best ask: {result['best_ask']['venue']} @ ${result['best_ask']['price']:,.2f}")
            print(f"✅ Mid price: ${result['mid']:,.2f}")
            print(f"📈 Spread: ${result['best_ask']['price'] - result['best_bid']['price']:,.2f}")
            print(f"📊 Venues queried: {result.get('venues_queried', len(exchanges))}")
            print(f"📊 Venues with data: {result.get('venues_with_data', len(result.get('all', [])))}")
        else:
            print("❌ No valid quotes received")
        
        # 2. L2 Order Book (using OKX as example)
        print("\n2️⃣ L2 Order Book (OKX)")
        print("-" * 30)
        okx_ex = make_exchanges(["okx"])[0]
        ob = await okx_ex.get_l2_orderbook(pair, depth=5)
        print(f"✅ Order book depth: {len(ob.bids)} bids, {len(ob.asks)} asks")
        print(f"✅ Best bid: ${ob.best_bid():,.2f}")
        print(f"✅ Best ask: ${ob.best_ask():,.2f}")
        print(f"✅ Mid: ${ob.mid():,.2f}")
        
        # 3. Price Impact Analysis
        print("\n3️⃣ Price Impact Analysis")
        print("-" * 30)
        trade_volume = 50000  # USDT
        for side in ["buy", "sell"]:
            avg_px, filled = walk_book(ob, side, trade_volume)
            impact = price_impact_pct(ob, side, trade_volume)
            print(f"📊 {side.upper()} ${trade_volume:,.0f} USDT:")
            print(f"   Avg execution: ${avg_px:,.2f}")
            print(f"   Filled: {filled:.6f} BTC")
            print(f"   Impact: {impact:.4f}%")
        
        # 4. Funding Rates
        print("\n4️⃣ Funding Rates (OKX)")
        print("-" * 30)
        try:
            funding = await okx_ex.get_funding_live_predicted(pair)
            summary = summarize_snapshot(funding)
            print(f"✅ Current rate: {funding.current_rate:.6f} ({funding.current_rate*100:.4f}%)")
            print(f"✅ Predicted next: {funding.predicted_next_rate:.6f} ({funding.predicted_next_rate*100:.4f}%)")
            print(f"✅ Interval: {funding.interval_hours} hours")
            print(f"📈 Current APR: {summary.current_apr:.4f}%")
            print(f"📈 Predicted APR: {summary.predicted_next_apr:.4f}%")
            print(f"📈 Daily return: {summary.daily_return:.6f} ({summary.daily_return*100:.4f}%)")
        except Exception as e:
            print(f"❌ Funding rate error: {e}")
        
        # 5. APR Calculation Utility
        print("\n5️⃣ APR Calculation Examples")
        print("-" * 30)
        from xetrade.services.funding import apr_from_periodic, apy_from_periodic
        
        # Example funding rates for different intervals
        examples = [
            (0.0001, 8.0, "8-hour funding"),
            (0.0001, 4.0, "4-hour funding"), 
            (0.0001, 1.0, "1-hour funding"),
        ]
        
        for rate, interval, desc in examples:
            apr = apr_from_periodic(rate, interval)
            apy = apy_from_periodic(rate, interval)
            print(f"📊 {desc}:")
            print(f"   Rate: {rate:.6f} ({rate*100:.4f}%)")
            print(f"   APR: {apr:.4f}%")
            print(f"   APY: {apy:.4f}%")
        
    except Exception as e:
        print(f"❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up HTTP session
        await http.close()

if __name__ == "__main__":
    asyncio.run(demo()) 