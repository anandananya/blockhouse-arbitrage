#!/usr/bin/env python3
"""
Task 3 Demo: Position & PnL Monitoring

This script demonstrates the position monitoring functionality including:
1. Creating a position from a filled order
2. Calculating real-time PnL
3. Live position monitoring
4. Position summary with all required fields
"""

import asyncio
import json
import time
from xetrade.exchanges.base import make_exchanges
from xetrade.models import Pair, OrderRequest
from xetrade.services.trading import UnifiedTradingService
from xetrade.services.position_monitor import PositionMonitorService

async def task3_demo():
    """Demonstrate Task 3: Position & PnL Monitoring."""
    print(" Task 3: Position & PnL Monitoring Demo")
    print("=" * 60)
    
    # Initialize services
    exchanges = make_exchanges(["okx"])
    trading_service = UnifiedTradingService(exchanges)
    position_service = PositionMonitorService(exchanges)
    pair = Pair.parse("BTC-USDT")
    
    print(f" Venue: okx")
    print(f" Pair: {pair.human()}")
    print()
    
    # Step 1: Place an order to create a position
    print("1 Placing Order to Create Position")
    print("-" * 40)
    
    order_request = OrderRequest(
        pair=pair,
        side="buy",
        order_type="LIMIT",
        quantity=0.001,
        price=50000.0,
    )
    
    placement_result = await trading_service.place_order(order_request, "okx")
    
    if not placement_result.success:
        print(f" Failed to place order: {placement_result.error}")
        return
    
    print(f" Order placed successfully:")
    print(f"   Order ID: {placement_result.order_id}")
    print(f"   Venue: {placement_result.venue}")
    print(f"   Side: {order_request.side}")
    print(f"   Quantity: {order_request.quantity}")
    print(f"   Price: ${order_request.price:,.2f}")
    print(f"   Latency: {placement_result.latency_ms:.2f}ms")
    
    # Step 2: Get position details from the order
    print(f"\n2 Getting Position Details")
    print("-" * 40)
    
    position_summary = await position_service.get_position_summary(
        placement_result.order_id, pair, "okx"
    )
    
    if position_summary["success"]:
        print(" Position Details:")
        print(f"   Connector Name: {position_summary['connector_name']}")
        print(f"   Pair Name: {position_summary['pair_name']}")
        print(f"   Entry Timestamp: {position_summary['entry_timestamp']}")
        print(f"   Entry Price: ${position_summary['entry_price']:,.2f}")
        print(f"   Quantity: {position_summary['quantity']}")
        print(f"   Position Side: {position_summary['position_side'].upper()}")
        
        if position_summary.get('current_price'):
            print(f"   Current Price: ${position_summary['current_price']:,.2f}")
            print(f"   Mark Price: ${position_summary['mark_price']:,.2f}")
            print(f"   Unrealized PnL: ${position_summary['unrealized_pnl']:,.2f}")
            print(f"   Unrealized PnL %: {position_summary['unrealized_pnl_pct']:+.2f}%")
            print(f"   Is Profitable: {position_summary['is_profitable']}")
            print(f"   PnL Color: {position_summary['pnl_color']}")
        
        print(f"   Latency: {position_summary['latency_ms']:.2f}ms")
    else:
        print(f" Failed to get position: {position_summary['error']}")
    
    # Step 3: Live position monitoring
    print(f"\n3 Live Position Monitoring")
    print("-" * 40)
    print("Monitoring position with 3 updates at 2-second intervals...")
    
    monitoring_results = await position_service.monitor_position_live(
        placement_result.order_id, pair, "okx", 
        interval_seconds=2, max_updates=3
    )
    
    for i, result in enumerate(monitoring_results, 1):
        print(f"\n Update {i}/{len(monitoring_results)}:")
        if result.success and result.position and result.pnl:
            position = result.position
            pnl = result.pnl
            
            # Format timestamps
            import datetime
            entry_time = datetime.datetime.fromtimestamp(position.entry_timestamp / 1000)
            pnl_time = datetime.datetime.fromtimestamp(pnl.ts_ms / 1000)
            
            print(f"    Venue: {position.venue}")
            print(f"    Pair: {position.pair.human()}")
            print(f"    Entry Time: {entry_time}")
            print(f"    Entry Price: ${position.entry_price:,.2f}")
            print(f"    Quantity: {position.quantity}")
            print(f"    Position Side: {position.position_side.upper()}")
            print(f"    Current Price: ${pnl.current_price:,.2f}")
            print(f"    Mark Price: ${pnl.mark_price:,.2f}")
            print(f"    Unrealized PnL: ${pnl.unrealized_pnl:,.2f} ({pnl.unrealized_pnl_pct:+.2f}%)")
            print(f"    Status: {' PROFIT' if pnl.is_profitable else ' LOSS' if pnl.unrealized_pnl < 0 else ' BREAKEVEN'}")
            print(f"     Latency: {result.latency_ms:.2f}ms")
            print(f"    PnL Time: {pnl_time}")
        else:
            print(f"    Error: {result.error}")
            print(f"     Latency: {result.latency_ms:.2f}ms")
    
    # Step 4: Demonstrate PnL calculation details
    print(f"\n4 PnL Calculation Details")
    print("-" * 40)
    
    if monitoring_results and monitoring_results[0].success and monitoring_results[0].position and monitoring_results[0].pnl:
        position = monitoring_results[0].position
        pnl = monitoring_results[0].pnl
        
        print(" PnL Calculation Breakdown:")
        print(f"   Position Type: {position.position_side.upper()}")
        print(f"   Entry Price: ${position.entry_price:,.2f}")
        print(f"   Current Price: ${pnl.current_price:,.2f}")
        print(f"   Position Size: {position.quantity} {position.pair.base}")
        
        if position.position_side == "long":
            price_change = pnl.current_price - position.entry_price
            print(f"   Price Change: ${price_change:,.2f} ({price_change/position.entry_price*100:+.2f}%)")
            print(f"   PnL Formula: (${pnl.current_price:,.2f} - ${position.entry_price:,.2f}) × {position.quantity}")
        else:
            price_change = position.entry_price - pnl.current_price
            print(f"   Price Change: ${price_change:,.2f} ({price_change/position.entry_price*100:+.2f}%)")
            print(f"   PnL Formula: (${position.entry_price:,.2f} - ${pnl.current_price:,.2f}) × {position.quantity}")
        
        print(f"   Unrealized PnL: ${pnl.unrealized_pnl:,.2f}")
        print(f"   PnL Percentage: {pnl.unrealized_pnl_pct:+.2f}%")
        print(f"   Status: {' PROFITABLE' if pnl.is_profitable else ' LOSING' if pnl.unrealized_pnl < 0 else ' BREAKEVEN'}")
    
    # Step 5: JSON output for API integration
    print(f"\n5 JSON Output for API Integration")
    print("-" * 40)
    
    final_summary = await position_service.get_position_summary(
        placement_result.order_id, pair, "okx"
    )
    
    print(" Complete Position Summary (JSON):")
    print(json.dumps(final_summary, indent=2))
    
    print(f"\n Task 3 Demo Completed!")
    print(f" All required fields implemented:")
    print(f"    connector_name (Exchange)")
    print(f"    pair_name")
    print(f"    entry_timestamp")
    print(f"    entry_price (average filled price)")
    print(f"    quantity")
    print(f"    position_side (long/short)")
    print(f"    NetPnL (real-time calculation)")

if __name__ == "__main__":
    asyncio.run(task3_demo()) 