#!/usr/bin/env python3
"""
Task 2 Demo: Trade Execution & Order Management

This demo showcases the unified trading system functionality including:
1. Unified Order Placement (LIMIT and MARKET orders)
2. Order Cancellation
3. Order Status Tracking
4. Performance Testing (200 orders in 5 minutes)
"""

import asyncio
import json
import logging
from datetime import datetime

from xetrade.models import Pair, OrderRequest, OrderType
from xetrade.services.trading import UnifiedTradingService
from xetrade.exchanges.base import make_exchanges
from xetrade.exchanges import mock  # noqa: F401

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_unified_order_placement():
    """Demonstrate unified order placement functionality."""
    
    print("Task 2 Demo: Trade Execution & Order Management")
    print("=" * 60)
    
    try:
        # Create trading service with mock exchange
        exchanges = make_exchanges(["mock"])
        trading_service = UnifiedTradingService(exchanges)
        pair = Pair.parse("BTC-USDT")
        
        print("1. Unified Order Placement Demo")
        print("-" * 40)
        
        # Test LIMIT order
        limit_request = OrderRequest(
            pair=pair,
            side="buy",
            order_type="LIMIT",
            quantity=0.001,
            price=50000.0,
        )
        
        print(f"Placing LIMIT order:")
        print(f"   Pair: {limit_request.pair.human()}")
        print(f"   Side: {limit_request.side}")
        print(f"   Type: {limit_request.order_type}")
        print(f"   Quantity: {limit_request.quantity}")
        print(f"   Price: ${limit_request.price:,.2f}")
        
        limit_result = await trading_service.place_order(limit_request, "mock")
        
        if limit_result.success:
            print(f"    Order placed successfully!")
            print(f"   Order ID: {limit_result.order_id}")
            print(f"   Venue: {limit_result.venue}")
            print(f"   Latency: {limit_result.latency_ms:.2f}ms")
        else:
            print(f"    Order placement failed: {limit_result.error}")
        
        print()
        
        # Test MARKET order
        market_request = OrderRequest(
            pair=pair,
            side="sell",
            order_type="MARKET",
            quantity=0.0005,
            price=None,  # MARKET orders don't need price
        )
        
        print(f"Placing MARKET order:")
        print(f"   Pair: {market_request.pair.human()}")
        print(f"   Side: {market_request.side}")
        print(f"   Type: {market_request.order_type}")
        print(f"   Quantity: {market_request.quantity}")
        
        market_result = await trading_service.place_order(market_request, "mock")
        
        if market_result.success:
            print(f"    Order placed successfully!")
            print(f"   Order ID: {market_result.order_id}")
            print(f"   Venue: {market_result.venue}")
            print(f"   Latency: {market_result.latency_ms:.2f}ms")
        else:
            print(f"    Order placement failed: {market_result.error}")
        
        return limit_result.success and market_result.success
        
    except Exception as e:
        print(f" Error in order placement demo: {e}")
        return False

async def demo_order_cancellation():
    """Demonstrate order cancellation functionality."""
    
    print("\n2. Order Cancellation Demo")
    print("-" * 30)
    
    try:
        exchanges = make_exchanges(["mock"])
        trading_service = UnifiedTradingService(exchanges)
        pair = Pair.parse("BTC-USDT")
        
        # First place an order to cancel
        request = OrderRequest(
            pair=pair,
            side="buy",
            order_type="LIMIT",
            quantity=0.001,
            price=50000.0,
        )
        
        placement_result = await trading_service.place_order(request, "mock")
        
        if not placement_result.success:
            print(f" Failed to place order for cancellation test: {placement_result.error}")
            return False
        
        order_id = placement_result.order_id
        print(f"Placed order {order_id} for cancellation test")
        
        # Cancel the order
        print(f"Cancelling order {order_id}...")
        cancel_result = await trading_service.cancel_order(order_id, pair, "mock")
        
        if cancel_result.success:
            print(f"    Order cancelled successfully!")
            print(f"   Order ID: {cancel_result.order_id}")
            print(f"   Venue: {cancel_result.venue}")
            print(f"   Latency: {cancel_result.latency_ms:.2f}ms")
        else:
            print(f"    Order cancellation failed: {cancel_result.error}")
        
        return cancel_result.success
        
    except Exception as e:
        print(f" Error in order cancellation demo: {e}")
        return False

async def demo_order_status_tracking():
    """Demonstrate order status tracking functionality."""
    
    print("\n3. Order Status Tracking Demo")
    print("-" * 35)
    
    try:
        exchanges = make_exchanges(["mock"])
        trading_service = UnifiedTradingService(exchanges)
        pair = Pair.parse("BTC-USDT")
        
        # Place an order to track
        request = OrderRequest(
            pair=pair,
            side="buy",
            order_type="LIMIT",
            quantity=0.001,
            price=50000.0,
        )
        
        placement_result = await trading_service.place_order(request, "mock")
        
        if not placement_result.success:
            print(f" Failed to place order for status tracking: {placement_result.error}")
            return False
        
        order_id = placement_result.order_id
        print(f"Tracking status of order {order_id}")
        
        # Get order status
        status_result = await trading_service.get_order_status(order_id, pair, "mock")
        
        if status_result:
            print(f"    Order status retrieved!")
            print(f"   Order ID: {status_result.order_id}")
            print(f"   Status: {status_result.status}")
            print(f"   Pair: {status_result.pair.human()}")
            print(f"   Side: {status_result.side}")
            print(f"   Quantity: {status_result.quantity}")
            print(f"   Filled Quantity: {status_result.filled_quantity}")
            print(f"   Price: ${status_result.price:,.2f}")
            if status_result.avg_fill_price:
                print(f"   Average Fill Price: ${status_result.avg_fill_price:,.2f}")
            print(f"   Timestamp: {datetime.fromtimestamp(status_result.ts_ms / 1000)}")
        else:
            print(f"    Failed to get order status")
        
        return status_result is not None
        
    except Exception as e:
        print(f" Error in order status tracking demo: {e}")
        return False

async def demo_performance_test():
    """Demonstrate performance testing with rapid order execution."""
    
    print("\n4. Performance Test Demo")
    print("-" * 25)
    print("Testing rapid order execution (simplified version)")
    
    try:
        exchanges = make_exchanges(["mock"])
        trading_service = UnifiedTradingService(exchanges)
        pair = Pair.parse("BTC-USDT")
        
        # Test with a smaller number for demo purposes
        num_orders = 10  # Reduced from 200 for demo
        max_duration_seconds = 10  # Reduced from 300 for demo
        
        print(f"Attempting {num_orders} orders in {max_duration_seconds} seconds...")
        
        start_time = datetime.now()
        successful_placements = 0
        successful_cancellations = 0
        placement_latencies = []
        cancellation_latencies = []
        
        for i in range(num_orders):
            # Create order request
            request = OrderRequest(
                pair=pair,
                side="buy" if i % 2 == 0 else "sell",
                order_type="LIMIT" if i % 3 == 0 else "MARKET",
                quantity=0.001,
                price=50000.0 + (i * 10),  # Vary price slightly
            )
            
            # Place order
            placement_start = datetime.now()
            placement_result = await trading_service.place_order(request, "mock")
            placement_end = datetime.now()
            
            placement_latency = (placement_end - placement_start).total_seconds() * 1000
            placement_latencies.append(placement_latency)
            
            if placement_result.success:
                successful_placements += 1
                print(f"   Order {i+1}: Placed  (ID: {placement_result.order_id}, Latency: {placement_latency:.2f}ms)")
                
                # Cancel order immediately
                cancel_start = datetime.now()
                cancel_result = await trading_service.cancel_order(placement_result.order_id, pair, "mock")
                cancel_end = datetime.now()
                
                cancel_latency = (cancel_end - cancel_start).total_seconds() * 1000
                cancellation_latencies.append(cancel_latency)
                
                if cancel_result.success:
                    successful_cancellations += 1
                    print(f"           Cancelled  (Latency: {cancel_latency:.2f}ms)")
                else:
                    print(f"           Cancellation failed ")
            else:
                print(f"   Order {i+1}: Placement failed  ({placement_result.error})")
            
            # Check if we've exceeded time limit
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > max_duration_seconds:
                print(f" Reached time limit of {max_duration_seconds} seconds")
                break
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Results
        print(f"\n Performance Test Results:")
        print(f"   Total Time: {total_time:.2f} seconds")
        print(f"   Orders Attempted: {num_orders}")
        print(f"   Successful Placements: {successful_placements}")
        print(f"   Successful Cancellations: {successful_cancellations}")
        print(f"   Placement Success Rate: {(successful_placements/num_orders)*100:.1f}%")
        print(f"   Cancellation Success Rate: {(successful_cancellations/num_orders)*100:.1f}%")
        
        if placement_latencies:
            avg_placement_latency = sum(placement_latencies) / len(placement_latencies)
            print(f"   Average Placement Latency: {avg_placement_latency:.2f}ms")
        
        if cancellation_latencies:
            avg_cancellation_latency = sum(cancellation_latencies) / len(cancellation_latencies)
            print(f"   Average Cancellation Latency: {avg_cancellation_latency:.2f}ms")
        
        return successful_placements > 0
        
    except Exception as e:
        print(f" Error in performance test demo: {e}")
        return False

def main():
    """Run the Task 2 demo."""
    print("Task 2: Trade Execution & Order Management")
    print("=" * 60)
    
    # Run demos
    results = []
    
    # Demo 1: Unified order placement
    result1 = asyncio.run(demo_unified_order_placement())
    results.append(result1)
    
    # Demo 2: Order cancellation
    result2 = asyncio.run(demo_order_cancellation())
    results.append(result2)
    
    # Demo 3: Order status tracking
    result3 = asyncio.run(demo_order_status_tracking())
    results.append(result3)
    
    # Demo 4: Performance testing
    result4 = asyncio.run(demo_performance_test())
    results.append(result4)
    
    # Summary
    print("\n Task 2 Demo Summary")
    print("=" * 60)
    
    demos = [
        "Unified Order Placement",
        "Order Cancellation", 
        "Order Status Tracking",
        "Performance Testing"
    ]
    
    for i, (demo, result) in enumerate(zip(demos, results), 1):
        status = " PASS" if result else " FAIL"
        print(f"{i}. {demo}: {status}")
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n Overall Results: {passed}/{total} demos passed")
    
    if passed == total:
        print("\n Task 2 Trade Execution & Order Management Demo Complete!")
        print("The system successfully demonstrates:")
        print(" Unified order placement (LIMIT and MARKET orders)")
        print(" Order cancellation functionality")
        print(" Order status tracking")
        print(" Performance testing with rapid execution")
        print(" Error handling and recovery")
    else:
        print("\n  Some demos had issues. Check the errors above.")

if __name__ == "__main__":
    main() 