#!/usr/bin/env python3
"""
Quick Performance Test - Demonstrates rapid order placement and cancellation
with a smaller number of orders for faster testing.
"""

import asyncio
import time
import random
from statistics import mean, median

from xetrade.exchanges.base import make_exchanges
from xetrade.models import Pair, OrderRequest
from xetrade.services.trading import UnifiedTradingService

async def quick_performance_test():
    """Run a quick performance test with 20 orders."""
    print("🚀 Quick Performance Test")
    print("=" * 40)
    print("📊 Target: 20 orders (mix of LIMIT and MARKET)")
    print("🏢 Venue: okx")
    print("🎯 Pair: BTC-USDT")
    print()
    
    # Initialize
    exchanges = make_exchanges(["okx"])
    trading_service = UnifiedTradingService(exchanges)
    pair = Pair.parse("BTC-USDT")
    
    results = []
    start_time = time.time()
    
    # Generate and execute orders
    for i in range(20):
        # Random order type (70% LIMIT, 30% MARKET)
        order_type = "LIMIT" if random.random() < 0.7 else "MARKET"
        side = random.choice(["buy", "sell"])
        quantity = round(random.uniform(0.001, 0.005), 6)
        price = round(50000 * random.uniform(0.95, 1.05), 2) if order_type == "LIMIT" else None
        
        request = OrderRequest(
            pair=pair,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
        )
        
        # Place order
        placement_start = time.time()
        placement_result = await trading_service.place_order(request, "okx")
        placement_latency = (time.time() - placement_start) * 1000
        
        # Cancel order if placement was successful
        cancellation_latency = 0.0
        cancellation_success = False
        
        if placement_result.success:
            cancel_start = time.time()
            cancel_result = await trading_service.cancel_order(placement_result.order_id, pair, "okx")
            cancellation_latency = (time.time() - cancel_start) * 1000
            cancellation_success = cancel_result.success
        
        results.append({
            "order_id": placement_result.order_id,
            "order_type": order_type,
            "side": side,
            "placement_success": placement_result.success,
            "placement_latency_ms": placement_latency,
            "cancellation_success": cancellation_success,
            "cancellation_latency_ms": cancellation_latency,
            "total_latency_ms": placement_latency + cancellation_latency,
        })
        
        # Progress indicator
        if (i + 1) % 5 == 0:
            print(f"   Completed {i + 1}/20 orders...")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate statistics
    successful_placements = sum(1 for r in results if r["placement_success"])
    successful_cancellations = sum(1 for r in results if r["cancellation_success"])
    
    placement_latencies = [r["placement_latency_ms"] for r in results if r["placement_success"]]
    cancellation_latencies = [r["cancellation_latency_ms"] for r in results if r["cancellation_success"]]
    total_latencies = [r["total_latency_ms"] for r in results if r["placement_success"]]
    
    # Print results
    print(f"\n📈 Quick Performance Results")
    print("=" * 40)
    print(f"⏱️  Total Time: {total_time:.2f} seconds")
    print(f"📊 Orders Attempted: {len(results)}")
    print(f"✅ Successful Placements: {successful_placements}")
    print(f"❌ Failed Placements: {len(results) - successful_placements}")
    print(f"✅ Successful Cancellations: {successful_cancellations}")
    print(f"❌ Failed Cancellations: {successful_placements - successful_cancellations}")
    
    placement_success_rate = (successful_placements / len(results)) * 100
    cancellation_success_rate = (successful_cancellations / successful_placements * 100) if successful_placements > 0 else 0
    
    print(f"📈 Placement Success Rate: {placement_success_rate:.1f}%")
    print(f"📈 Cancellation Success Rate: {cancellation_success_rate:.1f}%")
    
    if placement_latencies:
        print(f"\n⏱️  Placement Latency (ms):")
        print(f"   Average: {mean(placement_latencies):.2f}")
        print(f"   Median: {median(placement_latencies):.2f}")
        print(f"   Min: {min(placement_latencies):.2f}")
        print(f"   Max: {max(placement_latencies):.2f}")
    
    if cancellation_latencies:
        print(f"\n⏱️  Cancellation Latency (ms):")
        print(f"   Average: {mean(cancellation_latencies):.2f}")
        print(f"   Median: {median(cancellation_latencies):.2f}")
        print(f"   Min: {min(cancellation_latencies):.2f}")
        print(f"   Max: {max(cancellation_latencies):.2f}")
    
    if total_latencies:
        print(f"\n⏱️  Total Latency (ms):")
        print(f"   Average: {mean(total_latencies):.2f}")
        print(f"   Median: {median(total_latencies):.2f}")
        print(f"   Min: {min(total_latencies):.2f}")
        print(f"   Max: {max(total_latencies):.2f}")
    
    # Order type breakdown
    limit_orders = sum(1 for r in results if r["order_type"] == "LIMIT")
    market_orders = sum(1 for r in results if r["order_type"] == "MARKET")
    limit_success = sum(1 for r in results if r["order_type"] == "LIMIT" and r["placement_success"])
    market_success = sum(1 for r in results if r["order_type"] == "MARKET" and r["placement_success"])
    
    print(f"\n📋 Results by Order Type:")
    print(f"   LIMIT: {limit_success}/{limit_orders} ({(limit_success/limit_orders*100):.1f}%)")
    print(f"   MARKET: {market_success}/{market_orders} ({(market_success/market_orders*100):.1f}%)")
    
    print(f"\n🎯 Performance Assessment:")
    if total_time < 60:  # Should complete in under 1 minute
        print(f"   ✅ Fast execution ({total_time:.2f}s)")
    else:
        print(f"   ⚠️  Slow execution ({total_time:.2f}s)")
    
    if placement_success_rate >= 80:
        print(f"   ✅ Good placement success rate ({placement_success_rate:.1f}%)")
    else:
        print(f"   ⚠️  Low placement success rate ({placement_success_rate:.1f}%)")
    
    if cancellation_success_rate >= 90:
        print(f"   ✅ Good cancellation success rate ({cancellation_success_rate:.1f}%)")
    else:
        print(f"   ⚠️  Low cancellation success rate ({cancellation_success_rate:.1f}%)")
    
    print(f"\n✅ Quick performance test completed!")

if __name__ == "__main__":
    asyncio.run(quick_performance_test()) 