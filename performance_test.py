#!/usr/bin/env python3
"""
Performance Test for Task 2: Trade Execution & Order Management

This script demonstrates the system's ability to handle rapid execution by:
1. Placing 200 orders (mix of LIMIT and MARKET) across exchanges
2. Immediately cancelling each order after placement
3. Logging success/failure rates and average latency
4. Running within a 5-minute window
"""

import asyncio
import time
import json
import random
from dataclasses import dataclass
from typing import List, Dict
from statistics import mean, median

from xetrade.exchanges.base import make_exchanges
from xetrade.models import Pair, OrderRequest
from xetrade.services.trading import UnifiedTradingService, TradingResult

@dataclass
class TestResult:
    """Result of a single order placement and cancellation."""
    order_id: str
    venue: str
    order_type: str
    side: str
    quantity: float
    price: float
    placement_success: bool
    placement_latency_ms: float
    cancellation_success: bool
    cancellation_latency_ms: float
    total_latency_ms: float
    placement_error: str
    cancellation_error: str

class PerformanceTest:
    """Performance test for rapid order placement and cancellation."""
    
    def __init__(self, venues: List[str], pair: str = "BTC-USDT"):
        self.venues = venues
        self.pair = Pair.parse(pair)
        self.exchanges = make_exchanges(venues)
        self.trading_service = UnifiedTradingService(self.exchanges)
        self.results: List[TestResult] = []
        
        # Test parameters
        self.total_orders = 200
        self.time_window_minutes = 5
        self.start_time = None
        self.end_time = None
    
    async def generate_order_request(self) -> OrderRequest:
        """Generate a random order request for testing."""
        # Random order type (70% LIMIT, 30% MARKET)
        order_type = "LIMIT" if random.random() < 0.7 else "MARKET"
        
        # Random side
        side = random.choice(["buy", "sell"])
        
        # Random quantity (small amounts for testing)
        quantity = round(random.uniform(0.001, 0.01), 6)
        
        # Price (required for LIMIT orders)
        price = None
        if order_type == "LIMIT":
            # Generate price around current market price
            base_price = 50000  # Mock current price
            price = round(base_price * random.uniform(0.95, 1.05), 2)
        
        return OrderRequest(
            pair=self.pair,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
        )
    
    async def run_single_test(self, venue: str) -> TestResult:
        """Run a single order placement and cancellation test."""
        request = await self.generate_order_request()
        
        # Place order
        placement_start = time.time()
        placement_result = await self.trading_service.place_order(request, venue)
        placement_latency = (time.time() - placement_start) * 1000
        
        # Cancel order (if placement was successful)
        cancellation_latency = 0.0
        cancellation_success = False
        cancellation_error = "No order to cancel"
        
        if placement_result.success:
            cancel_start = time.time()
            cancel_result = await self.trading_service.cancel_order(
                placement_result.order_id, self.pair, venue
            )
            cancellation_latency = (time.time() - cancel_start) * 1000
            cancellation_success = cancel_result.success
            cancellation_error = cancel_result.error or "Success"
        
        return TestResult(
            order_id=placement_result.order_id or "N/A",
            venue=venue,
            order_type=request.order_type,
            side=request.side,
            quantity=request.quantity,
            price=request.price or 0.0,
            placement_success=placement_result.success,
            placement_latency_ms=placement_latency,
            cancellation_success=cancellation_success,
            cancellation_latency_ms=cancellation_latency,
            total_latency_ms=placement_latency + cancellation_latency,
            placement_error=placement_result.error or "Success",
            cancellation_error=cancellation_error,
        )
    
    async def run_performance_test(self):
        """Run the complete performance test."""
        print("🚀 Starting Performance Test")
        print("=" * 50)
        print(f"📊 Target: {self.total_orders} orders in {self.time_window_minutes} minutes")
        print(f"🏢 Venues: {', '.join(self.venues)}")
        print(f"🎯 Pair: {self.pair.human()}")
        print()
        
        self.start_time = time.time()
        end_time = self.start_time + (self.time_window_minutes * 60)
        
        # Run tests concurrently
        tasks = []
        for i in range(self.total_orders):
            venue = random.choice(self.venues)
            task = asyncio.create_task(self.run_single_test(venue))
            tasks.append(task)
            
            # Small delay to avoid overwhelming the system
            if i % 10 == 0:
                await asyncio.sleep(0.1)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, TestResult):
                self.results.append(result)
            else:
                # Handle exceptions
                self.results.append(TestResult(
                    order_id="ERROR",
                    venue="unknown",
                    order_type="ERROR",
                    side="unknown",
                    quantity=0.0,
                    price=0.0,
                    placement_success=False,
                    placement_latency_ms=0.0,
                    cancellation_success=False,
                    cancellation_latency_ms=0.0,
                    total_latency_ms=0.0,
                    placement_error=str(result),
                    cancellation_error="N/A",
                ))
        
        self.end_time = time.time()
        self.print_results()
    
    def print_results(self):
        """Print comprehensive test results."""
        print("\n📈 Performance Test Results")
        print("=" * 50)
        
        # Basic statistics
        total_time = self.end_time - self.start_time
        successful_placements = sum(1 for r in self.results if r.placement_success)
        successful_cancellations = sum(1 for r in self.results if r.cancellation_success)
        
        print(f"⏱️  Total Time: {total_time:.2f} seconds")
        print(f"📊 Orders Attempted: {len(self.results)}")
        print(f"✅ Successful Placements: {successful_placements}")
        print(f"❌ Failed Placements: {len(self.results) - successful_placements}")
        print(f"✅ Successful Cancellations: {successful_cancellations}")
        print(f"❌ Failed Cancellations: {successful_placements - successful_cancellations}")
        
        # Success rates
        placement_success_rate = (successful_placements / len(self.results)) * 100
        cancellation_success_rate = (successful_cancellations / successful_placements * 100) if successful_placements > 0 else 0
        
        print(f"📈 Placement Success Rate: {placement_success_rate:.1f}%")
        print(f"📈 Cancellation Success Rate: {cancellation_success_rate:.1f}%")
        
        # Latency statistics
        placement_latencies = [r.placement_latency_ms for r in self.results if r.placement_success]
        cancellation_latencies = [r.cancellation_latency_ms for r in self.results if r.cancellation_success]
        total_latencies = [r.total_latency_ms for r in self.results if r.placement_success]
        
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
        
        # Venue breakdown
        print(f"\n🏢 Results by Venue:")
        venue_stats = {}
        for result in self.results:
            venue = result.venue
            if venue not in venue_stats:
                venue_stats[venue] = {"total": 0, "successful": 0}
            venue_stats[venue]["total"] += 1
            if result.placement_success:
                venue_stats[venue]["successful"] += 1
        
        for venue, stats in venue_stats.items():
            success_rate = (stats["successful"] / stats["total"]) * 100
            print(f"   {venue}: {stats['successful']}/{stats['total']} ({success_rate:.1f}%)")
        
        # Order type breakdown
        print(f"\n📋 Results by Order Type:")
        type_stats = {}
        for result in self.results:
            order_type = result.order_type
            if order_type not in type_stats:
                type_stats[order_type] = {"total": 0, "successful": 0}
            type_stats[order_type]["total"] += 1
            if result.placement_success:
                type_stats[order_type]["successful"] += 1
        
        for order_type, stats in type_stats.items():
            success_rate = (stats["successful"] / stats["total"]) * 100
            print(f"   {order_type}: {stats['successful']}/{stats['total']} ({success_rate:.1f}%)")
        
        # Performance assessment
        print(f"\n🎯 Performance Assessment:")
        if total_time <= (self.time_window_minutes * 60):
            print(f"   ✅ Completed within {self.time_window_minutes}-minute window")
        else:
            print(f"   ❌ Exceeded {self.time_window_minutes}-minute window")
        
        if placement_success_rate >= 80:
            print(f"   ✅ Good placement success rate ({placement_success_rate:.1f}%)")
        else:
            print(f"   ⚠️  Low placement success rate ({placement_success_rate:.1f}%)")
        
        if cancellation_success_rate >= 90:
            print(f"   ✅ Good cancellation success rate ({cancellation_success_rate:.1f}%)")
        else:
            print(f"   ⚠️  Low cancellation success rate ({cancellation_success_rate:.1f}%)")
        
        # Save detailed results to file
        self.save_detailed_results()
    
    def save_detailed_results(self):
        """Save detailed results to a JSON file."""
        detailed_results = []
        for result in self.results:
            detailed_results.append({
                "order_id": result.order_id,
                "venue": result.venue,
                "order_type": result.order_type,
                "side": result.side,
                "quantity": result.quantity,
                "price": result.price,
                "placement_success": result.placement_success,
                "placement_latency_ms": result.placement_latency_ms,
                "cancellation_success": result.cancellation_success,
                "cancellation_latency_ms": result.cancellation_latency_ms,
                "total_latency_ms": result.total_latency_ms,
                "placement_error": result.placement_error,
                "cancellation_error": result.cancellation_error,
            })
        
        with open("performance_test_results.json", "w") as f:
            json.dump({
                "test_config": {
                    "total_orders": self.total_orders,
                    "time_window_minutes": self.time_window_minutes,
                    "venues": self.venues,
                    "pair": self.pair.human(),
                },
                "results": detailed_results,
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: performance_test_results.json")

async def main():
    """Run the performance test."""
    # Test configuration
    venues = ["okx"]  # Add more venues as they implement trading
    pair = "BTC-USDT"
    
    test = PerformanceTest(venues, pair)
    await test.run_performance_test()

if __name__ == "__main__":
    asyncio.run(main()) 