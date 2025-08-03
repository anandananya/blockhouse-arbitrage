# src/services/position_monitor.py
from __future__ import annotations
import time
from typing import List, Optional, Dict
from dataclasses import dataclass
import asyncio

from xetrade.exchanges.base import BaseExchange
from xetrade.models import Pair, Position, PositionPnL, OrderStatus

@dataclass(frozen=True)
class PositionMonitorResult:
    """Result of position monitoring operation."""
    success: bool
    position: Optional[Position]
    pnl: Optional[PositionPnL]
    error: Optional[str]
    latency_ms: float

class PositionMonitorService:
    """
    Service for monitoring positions and calculating real-time PnL.
    """
    
    def __init__(self, exchanges: List[BaseExchange]):
        self.exchanges = exchanges
        self.trading_exchanges = [ex for ex in exchanges if ex.supports_trading]
    
    async def get_position_from_order(self, order_id: str, pair: Pair, venue: str) -> PositionMonitorResult:
        """
        Get position details from a filled order.
        
        Args:
            order_id: Order ID of the filled order
            pair: Trading pair
            venue: Exchange venue
        
        Returns:
            PositionMonitorResult with position details and PnL calculation
        """
        start_time = time.time()
        
        # Find the target exchange
        target_exchange = next((ex for ex in self.trading_exchanges if ex.name == venue), None)
        if not target_exchange:
            return PositionMonitorResult(
                success=False,
                position=None,
                pnl=None,
                error=f"Venue '{venue}' not found or doesn't support trading",
                latency_ms=(time.time() - start_time) * 1000
            )
        
        try:
            # Get position from order
            position = await target_exchange.get_position_from_order(order_id, pair)
            
            if not position:
                return PositionMonitorResult(
                    success=False,
                    position=None,
                    pnl=None,
                    error=f"No position found for order {order_id}",
                    latency_ms=(time.time() - start_time) * 1000
                )
            
            # Calculate PnL
            pnl = await target_exchange.calculate_position_pnl(position)
            
            return PositionMonitorResult(
                success=True,
                position=position,
                pnl=pnl,
                error=None,
                latency_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return PositionMonitorResult(
                success=False,
                position=None,
                pnl=None,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
    
    async def monitor_position_live(self, order_id: str, pair: Pair, venue: str, 
                                   interval_seconds: int = 30, max_updates: int = 10) -> List[PositionMonitorResult]:
        """
        Monitor a position live with periodic updates.
        
        Args:
            order_id: Order ID to monitor
            pair: Trading pair
            venue: Exchange venue
            interval_seconds: Update interval in seconds
            max_updates: Maximum number of updates to perform
        
        Returns:
            List of PositionMonitorResult with live updates
        """
        results = []
        
        for i in range(max_updates):
            result = await self.get_position_from_order(order_id, pair, venue)
            results.append(result)
            
            if not result.success:
                break  # Stop if we can't get position data
            
            # Wait for next update (except for the last iteration)
            if i < max_updates - 1:
                await asyncio.sleep(interval_seconds)
        
        return results
    
    async def get_position_summary(self, order_id: str, pair: Pair, venue: str) -> Dict:
        """
        Get a comprehensive position summary including PnL details.
        
        Args:
            order_id: Order ID of the filled order
            pair: Trading pair
            venue: Exchange venue
        
        Returns:
            Dictionary with position summary and PnL information
        """
        result = await self.get_position_from_order(order_id, pair, venue)
        
        if not result.success:
            return {
                "success": False,
                "error": result.error,
                "latency_ms": result.latency_ms,
            }
        
        position = result.position
        pnl = result.pnl
        
        summary = {
            "success": True,
            "connector_name": position.venue,
            "pair_name": position.pair.human(),
            "entry_timestamp": position.entry_timestamp,
            "entry_price": position.entry_price,
            "quantity": position.quantity,
            "position_side": position.position_side,
            "latency_ms": result.latency_ms,
        }
        
        if pnl:
            summary.update({
                "current_price": pnl.current_price,
                "mark_price": pnl.mark_price,
                "unrealized_pnl": pnl.unrealized_pnl,
                "unrealized_pnl_pct": pnl.unrealized_pnl_pct,
                "is_profitable": pnl.is_profitable,
                "pnl_color": pnl.pnl_color,
                "pnl_timestamp": pnl.ts_ms,
            })
        else:
            summary.update({
                "current_price": None,
                "mark_price": None,
                "unrealized_pnl": None,
                "unrealized_pnl_pct": None,
                "is_profitable": None,
                "pnl_color": "unknown",
                "pnl_timestamp": None,
            })
        
        return summary 