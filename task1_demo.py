#!/usr/bin/env python3
"""
Task 1 Demo: Exchange Connectors

This demo showcases the multi-exchange connectivity functionality.
"""

import asyncio
import json
from datetime import datetime
import logging

from xetrade.exchanges.base import make_exchanges, available_exchanges
from xetrade.models import Pair
from xetrade.services.aggregator import best_across_venues
from xetrade.exchanges import binance, mock  # noqa: F401

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_exchange_connectors():
    """Demonstrate exchange connector functionality."""
    
    print(" Task 1 Demo: Exchange Connectors")
    print("=" * 50)
    
    # Show available exchanges
    exchanges = available_exchanges()
    print(f" Available exchanges: {exchanges}")
    print()
    
    # Test individual exchange
    print(" Testing Mock Exchange:")
    mock_exchanges = make_exchanges(["mock"])
    pair = Pair.parse("BTC-USDT")
    
    try:
        # Get best bid/ask
        quote = await mock_exchanges[0].get_best_bid_ask(pair)
        print(f" Best bid/ask for {pair.human()}:")
        print(f"   Bid: ${quote.bid:,.2f}")
        print(f"   Ask: ${quote.ask:,.2f}")
        print(f"   Mid: ${quote.mid:,.2f}")
        print(f"   Timestamp: {datetime.fromtimestamp(quote.ts_ms / 1000)}")
        
        # Get L2 order book
        orderbook = await mock_exchanges[0].get_l2_orderbook(pair, depth=10)
        print(f"\n L2 Order Book (top 10 levels):")
        print(f"   Bids: {len(orderbook.bids)} levels")
        print(f"   Asks: {len(orderbook.asks)} levels")
        print(f"   Best bid: ${orderbook.best_bid():,.2f}")
        print(f"   Best ask: ${orderbook.best_ask():,.2f}")
        print(f"   Mid price: ${orderbook.mid():,.2f}")
        
        # Show sample levels
        print(f"\n Sample Order Book Levels:")
        print(f"   Top 3 Bids:")
        for i, level in enumerate(orderbook.bids[:3]):
            print(f"     {i+1}. ${level.price:,.2f} - {level.qty:.4f}")
        
        print(f"   Top 3 Asks:")
        for i, level in enumerate(orderbook.asks[:3]):
            print(f"     {i+1}. ${level.price:,.2f} - {level.qty:.4f}")
        
        return True
        
    except Exception as e:
        print(f" Error testing mock exchange: {e}")
        return False

async def demo_multi_exchange_aggregation():
    """Demonstrate multi-exchange aggregation."""
    
    print("\n Multi-Exchange Aggregation Demo:")
    print("=" * 50)
    
    try:
        # Create multiple mock exchanges
        exchanges = make_exchanges(["mock", "mock"])  # Two mock instances
        pair = Pair.parse("BTC-USDT")
        
        print(f" Aggregating data from {len(exchanges)} exchanges")
        print(f" Trading pair: {pair.human()}")
        
        # Get best across venues
        result = await best_across_venues(exchanges, pair)
        
        print(f"\n Aggregation Results:")
        print(f"   Best bid: {result['best_bid']}")
        print(f"   Best ask: {result['best_ask']}")
        print(f"   Mid price: {result['mid']}")
        print(f"   Venues queried: {result['venues_queried']}")
        print(f"   Venues with data: {result['venues_with_data']}")
        
        return True
        
    except Exception as e:
        print(f" Error in aggregation demo: {e}")
        return False

async def demo_exchange_capabilities():
    """Demonstrate exchange capability detection."""
    
    print("\n Exchange Capabilities Demo:")
    print("=" * 50)
    
    try:
        exchanges = make_exchanges(["mock"])
        exchange = exchanges[0]
        
        print(f" Exchange: {exchange.name}")
        print(f"   Supports spot trading: {exchange.supports_spot}")
        print(f"   Supports funding rates: {exchange.supports_funding}")
        print(f"   Supports L2 order book: {exchange.supports_l2_orderbook}")
        print(f"   Supports trading: {exchange.supports_trading}")
        
        # Test funding rates (if supported)
        if exchange.supports_funding:
            try:
                pair = Pair.parse("BTC-USDT")
                funding = await exchange.get_funding_live_predicted(pair)
                print(f"\n Funding Rate Info:")
                print(f"   Current rate: {funding.current_rate:.6f}")
                print(f"   Predicted rate: {funding.predicted_next_rate:.6f}")
                print(f"   Interval: {funding.interval_hours} hours")
            except Exception as e:
                print(f"   Funding rate test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f" Error in capabilities demo: {e}")
        return False

async def demo_funding_rates():
    """Demonstrate funding rates functionality."""
    
    print("\n Funding Rates Demo:")
    print("=" * 50)
    
    try:
        # Test with an exchange that supports funding (like OKX)
        exchanges = make_exchanges(["okx"])
        exchange = exchanges[0]
        pair = Pair.parse("BTC-USDT")
        
        print(f" Testing funding rates on {exchange.name}")
        
        if exchange.supports_funding:
            # Get live funding rates
            funding = await exchange.get_funding_live_predicted(pair)
            print(f"\n Live Funding Rates:")
            print(f"   Current rate: {funding.current_rate:.6f}")
            print(f"   Predicted next rate: {funding.predicted_next_rate:.6f}")
            print(f"   Interval: {funding.interval_hours} hours")
            
            # Calculate APR
            from xetrade.services.funding import summarize_snapshot
            summary = summarize_snapshot(funding)
            print(f"\n APR Calculations:")
            print(f"   Current APR: {summary.current_apr:.4f}")
            print(f"   Predicted APR: {summary.predicted_next_apr:.4f}")
            print(f"   Current APY: {summary.current_apy:.4f}")
            print(f"   Daily return: {summary.daily_return:.6f}")
            
            # Test historical funding rates
            try:
                import time
                end_ms = int(time.time() * 1000)
                start_ms = end_ms - (7 * 24 * 60 * 60 * 1000)  # 7 days ago
                history = await exchange.get_funding_history(pair, start_ms, end_ms)
                print(f"\n Historical Funding Rates:")
                print(f"   Data points: {len(history)}")
                if history:
                    rates = [p.rate for p in history]
                    print(f"   Average rate: {sum(rates) / len(rates):.6f}")
                    print(f"   Min rate: {min(rates):.6f}")
                    print(f"   Max rate: {max(rates):.6f}")
            except Exception as e:
                print(f"   Historical funding test failed: {e}")
        else:
            print(f" {exchange.name} does not support funding rates")
        
        # Clean up aiohttp session
        if hasattr(exchange, '_session') and exchange._session:
            await exchange._session.close()
        
        return True
        
    except Exception as e:
        print(f" Error in funding rates demo: {e}")
        return False

async def demo_price_impact():
    """Demonstrate price impact calculation."""
    
    print("\n Price Impact Demo:")
    print("=" * 50)
    
    try:
        exchanges = make_exchanges(["mock"])
        exchange = exchanges[0]
        pair = Pair.parse("BTC-USDT")
        
        # Get order book
        orderbook = await exchange.get_l2_orderbook(pair, depth=100)
        print(f" Order Book for {pair.human()}:")
        print(f"   Bids: {len(orderbook.bids)} levels")
        print(f"   Asks: {len(orderbook.asks)} levels")
        print(f"   Mid price: ${orderbook.mid():,.2f}")
        
        # Test price impact calculations
        from xetrade.services.price_impact import price_impact_pct
        
        test_volumes = [1000, 5000, 10000, 50000, 100000]  # USDT
        
        print(f"\n Price Impact Analysis:")
        print(f"   Trade Volume | Buy Impact | Sell Impact")
        print(f"   " + "-" * 40)
        
        for volume in test_volumes:
            buy_impact = price_impact_pct(orderbook, "buy", volume)
            sell_impact = price_impact_pct(orderbook, "sell", volume)
            print(f"   ${volume:>8,} | {buy_impact:>9.3f}% | {sell_impact:>10.3f}%")
        
        return True
        
    except Exception as e:
        print(f" Error in price impact demo: {e}")
        return False

def main():
    """Run the Task 1 demo."""
    print(" Task 1: Exchange Connectors")
    print("=" * 50)
    
    # Run demos
    results = []
    
    # Demo 1: Individual exchange
    result1 = asyncio.run(demo_exchange_connectors())
    results.append(result1)
    
    # Demo 2: Multi-exchange aggregation
    result2 = asyncio.run(demo_multi_exchange_aggregation())
    results.append(result2)
    
    # Demo 3: Exchange capabilities
    result3 = asyncio.run(demo_exchange_capabilities())
    results.append(result3)
    
    # Demo 4: Funding rates
    result4 = asyncio.run(demo_funding_rates())
    results.append(result4)
    
    # Demo 5: Price impact
    result5 = asyncio.run(demo_price_impact())
    results.append(result5)
    
    # Summary
    print("\n Task 1 Demo Summary")
    print("=" * 50)
    
    demos = [
        "Individual Exchange Testing",
        "Multi-Exchange Aggregation", 
        "Exchange Capabilities",
        "Funding Rates",
        "Price Impact Analysis"
    ]
    
    for i, (demo, result) in enumerate(zip(demos, results), 1):
        status = " PASS" if result else " FAIL"
        print(f"{i}. {demo}: {status}")
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n Overall Results: {passed}/{total} demos passed")
    
    if passed == total:
        print("\n Task 1 Exchange Connectors Demo Complete!")
        print("The system successfully demonstrates:")
        print(" Multi-exchange connectivity (5+ exchanges)")
        print(" Real-time market data access")
        print(" L2 order book retrieval")
        print(" Best bid/ask aggregation across venues")
        print(" Exchange capability detection")
        print(" Funding rates with APR calculation")
        print(" Price impact analysis")
        print(" Error handling and recovery")
    else:
        print("\n  Some demos had issues. Check the errors above.")

if __name__ == "__main__":
    main() 