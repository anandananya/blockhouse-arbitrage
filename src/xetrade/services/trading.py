# src/services/trading.py
from __future__ import annotations
import asyncio
import time
from typing import List, Optional
from dataclasses import dataclass

from xetrade.exchanges.base import BaseExchange
from xetrade.models import (
    OrderRequest, OrderResponse, OrderStatusResponse, CancelResponse,
    Pair, OrderStatus
)

@dataclass(frozen=True)
class TradingResult:
    """Result of a trading operation across multiple venues."""
    success: bool
    venue: str
    order_id: Optional[str]
    error: Optional[str]
    latency_ms: float

class UnifiedTradingService:
    """
    Unified trading service that can place, cancel, and track orders
    across multiple exchanges.
    """
    
    def __init__(self, exchanges: List[BaseExchange]):
        self.exchanges = exchanges
        self.trading_exchanges = [ex for ex in exchanges if ex.supports_trading]
    
    async def place_order(self, request: OrderRequest, venue: Optional[str] = None) -> TradingResult:
        """
        Place an order on a specific venue or find the best venue.
        
        Args:
            request: Order request details
            venue: Specific venue to use (if None, will try all trading venues)
        
        Returns:
            TradingResult with success status and order details
        """
        start_time = time.time()
        
        if venue:
            # Place on specific venue
            target_exchange = next((ex for ex in self.trading_exchanges if ex.name == venue), None)
            if not target_exchange:
                return TradingResult(
                    success=False,
                    venue=venue,
                    order_id=None,
                    error=f"Venue '{venue}' not found or doesn't support trading",
                    latency_ms=(time.time() - start_time) * 1000
                )
            
            try:
                response = await target_exchange.place_order(request)
                return TradingResult(
                    success=True,
                    venue=target_exchange.name,
                    order_id=response.order_id,
                    error=None,
                    latency_ms=(time.time() - start_time) * 1000
                )
            except Exception as e:
                return TradingResult(
                    success=False,
                    venue=target_exchange.name,
                    order_id=None,
                    error=str(e),
                    latency_ms=(time.time() - start_time) * 1000
                )
        else:
            # Try all trading venues until one succeeds
            for exchange in self.trading_exchanges:
                try:
                    response = await exchange.place_order(request)
                    return TradingResult(
                        success=True,
                        venue=exchange.name,
                        order_id=response.order_id,
                        error=None,
                        latency_ms=(time.time() - start_time) * 1000
                    )
                except Exception as e:
                    continue  # Try next venue
            
            # All venues failed
            return TradingResult(
                success=False,
                venue="all",
                order_id=None,
                error="All trading venues failed",
                latency_ms=(time.time() - start_time) * 1000
            )
    
    async def cancel_order(self, order_id: str, pair: Pair, venue: str) -> TradingResult:
        """
        Cancel an order on a specific venue.
        
        Args:
            order_id: Order ID to cancel
            pair: Trading pair
            venue: Venue where the order was placed
        
        Returns:
            TradingResult with cancellation status
        """
        start_time = time.time()
        
        target_exchange = next((ex for ex in self.trading_exchanges if ex.name == venue), None)
        if not target_exchange:
            return TradingResult(
                success=False,
                venue=venue,
                order_id=order_id,
                error=f"Venue '{venue}' not found or doesn't support trading",
                latency_ms=(time.time() - start_time) * 1000
            )
        
        try:
            response = await target_exchange.cancel_order(order_id, pair)
            return TradingResult(
                success=response.success,
                venue=venue,
                order_id=order_id,
                error=None if response.success else response.message,
                latency_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return TradingResult(
                success=False,
                venue=venue,
                order_id=order_id,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
    
    async def get_order_status(self, order_id: str, pair: Pair, venue: str) -> Optional[OrderStatusResponse]:
        """
        Get the status of an order on a specific venue.
        
        Args:
            order_id: Order ID to check
            pair: Trading pair
            venue: Venue where the order was placed
        
        Returns:
            OrderStatusResponse or None if venue not found
        """
        target_exchange = next((ex for ex in self.trading_exchanges if ex.name == venue), None)
        if not target_exchange:
            return None
        
        try:
            return await target_exchange.get_order_status(order_id, pair)
        except Exception:
            return None
    
    async def place_and_cancel_rapid(self, request: OrderRequest, venue: str) -> tuple[TradingResult, TradingResult]:
        """
        Place an order and immediately cancel it for performance testing.
        
        Args:
            request: Order request
            venue: Venue to use
        
        Returns:
            Tuple of (placement_result, cancellation_result)
        """
        # Place order
        placement_result = await self.place_order(request, venue)
        
        if not placement_result.success:
            # Return failed placement with dummy cancellation
            return placement_result, TradingResult(
                success=False,
                venue=venue,
                order_id=None,
                error="No order to cancel",
                latency_ms=0.0
            )
        
        # Cancel order
        cancel_result = await self.cancel_order(placement_result.order_id, request.pair, venue)
        
        return placement_result, cancel_result 