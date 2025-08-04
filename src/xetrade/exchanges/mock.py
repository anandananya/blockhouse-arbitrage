# src/xetrade/exchanges/mock.py
from __future__ import annotations
import time
import random
from typing import List, Optional

from xetrade.exchanges.base import BaseExchange, register_exchange
from xetrade.models import Pair, Quote, OrderBook, Level, OrderRequest, OrderResponse, OrderStatusResponse, CancelResponse, OrderStatus, Position, PositionPnL, PositionSide

@register_exchange
class MockExchange(BaseExchange):
    """Mock exchange for demo purposes - generates realistic order book data."""
    
    name = "mock"
    supports_spot = True
    supports_funding = False
    supports_l2_orderbook = True
    supports_trading = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_prices = {
            "BTC-USDT": 50000.0,
            "ETH-USDT": 3000.0,
            "SOL-USDT": 100.0,
            "DOGE-USDT": 0.08,
        }
        self.price_volatility = 0.001  # 0.1% volatility
    
    def _generate_realistic_price(self, base_price: float) -> float:
        """Generate realistic price with some volatility."""
        # Add some random walk
        change = random.gauss(0, self.price_volatility)
        new_price = base_price * (1 + change)
        return max(new_price, base_price * 0.9)  # Don't go too low
    
    def _generate_order_book_levels(self, base_price: float, side: str, depth: int) -> List[Level]:
        """Generate realistic order book levels."""
        levels = []
        
        for i in range(depth):
            if side == "bid":
                # Bids: prices decrease, quantities increase
                price_offset = -i * (base_price * 0.0001)  # 0.01% steps
                price = base_price + price_offset
                quantity = random.uniform(0.1, 10.0) * (1 + i * 0.1)  # More quantity at lower prices
            else:
                # Asks: prices increase, quantities decrease
                price_offset = i * (base_price * 0.0001)  # 0.01% steps
                price = base_price + price_offset
                quantity = random.uniform(0.1, 10.0) * (1 - i * 0.05)  # Less quantity at higher prices
            
            levels.append(Level(price=price, qty=quantity))
        
        return levels
    
    async def get_best_bid_ask(self, pair: Pair) -> Quote:
        """Get best bid/ask for the pair."""
        base_price = self.base_prices.get(pair.human(), 100.0)
        
        # Update base price with some volatility
        self.base_prices[pair.human()] = self._generate_realistic_price(base_price)
        current_price = self.base_prices[pair.human()]
        
        # Generate realistic spread (0.01% to 0.1%)
        spread_pct = random.uniform(0.0001, 0.001)
        spread = current_price * spread_pct
        
        bid = current_price - spread / 2
        ask = current_price + spread / 2
        
        return Quote(
            bid=bid,
            ask=ask,
            ts_ms=int(time.time() * 1000)
        )
    
    async def get_l2_orderbook(self, pair: Pair, depth: int = 100) -> OrderBook:
        """Get L2 order book with realistic data."""
        base_price = self.base_prices.get(pair.human(), 100.0)
        
        # Update base price with some volatility
        self.base_prices[pair.human()] = self._generate_realistic_price(base_price)
        current_price = self.base_prices[pair.human()]
        
        # Generate realistic order book
        bids = self._generate_order_book_levels(current_price, "bid", depth)
        asks = self._generate_order_book_levels(current_price, "ask", depth)
        
        # Sort bids descending, asks ascending
        bids.sort(key=lambda x: x.price, reverse=True)
        asks.sort(key=lambda x: x.price)
        
        return OrderBook(
            bids=bids,
            asks=asks,
            ts_ms=int(time.time() * 1000)
        )
    
    def format_symbol(self, pair: Pair) -> str:
        """Format pair for this exchange."""
        return pair.concat()
    
    # ---- trading (order management) ----
    async def place_order(self, request: OrderRequest) -> OrderResponse:
        """
        Place a new order on mock exchange.
        Note: This is a mock implementation for demonstration.
        """
        ts_ms = int(time.time() * 1000)
        
        # Mock order ID generation
        order_id = f"mock_{ts_ms}_{hash(request.pair.human()) % 10000}"
        
        # Validate price for LIMIT orders
        if request.order_type == "LIMIT" and request.price is None:
            raise ValueError("Price is required for LIMIT orders")
        
        return OrderResponse(
            order_id=order_id,
            venue=self.name,
            pair=request.pair,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price,
            status=OrderStatus.PENDING,
            ts_ms=ts_ms,
        )

    async def cancel_order(self, order_id: str, pair: Pair) -> CancelResponse:
        """
        Cancel an existing order on mock exchange.
        Note: This is a mock implementation for demonstration.
        """
        ts_ms = int(time.time() * 1000)
        
        return CancelResponse(
            order_id=order_id,
            venue=self.name,
            success=True,
            message="Order cancelled successfully",
            ts_ms=ts_ms,
        )

    async def get_order_status(self, order_id: str, pair: Pair) -> OrderStatusResponse:
        """
        Get the current status of an order on mock exchange.
        Note: This is a mock implementation for demonstration.
        """
        ts_ms = int(time.time() * 1000)
        
        # Mock different statuses for demonstration
        import random
        statuses = [OrderStatus.OPEN, OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.PARTIALLY_FILLED]
        status = random.choice(statuses)
        
        return OrderStatusResponse(
            order_id=order_id,
            venue=self.name,
            pair=pair,
            side="buy",  # Mock data
            order_type="LIMIT",  # Mock data
            quantity=0.001,  # Mock data
            filled_quantity=0.0 if status == OrderStatus.OPEN else 0.001,
            price=50000.0,  # Mock data
            avg_fill_price=50000.0 if status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED] else None,
            status=status,
            ts_ms=ts_ms,
        )

    # ---- position monitoring ----
    async def get_position_from_order(self, order_id: str, pair: Pair) -> Optional[Position]:
        """
        Get position details from a filled order on mock exchange.
        Note: This is a mock implementation for demonstration.
        """
        ts_ms = int(time.time() * 1000)
        
        # Mock position creation - in reality, you'd query the exchange API
        # For demonstration, create a mock position from the order ID
        
        # Extract side from order ID (mock logic)
        import random
        side = random.choice(["buy", "sell"])
        position_side = "long" if side == "buy" else "short"
        
        # Mock entry price and quantity
        base_price = self.base_prices.get(pair.human(), 50000.0)
        entry_price = base_price + random.uniform(-1000, 1000)  # Around base price
        quantity = 0.001  # Small position for demo
        
        return Position(
            order_id=order_id,
            venue=self.name,
            pair=pair,
            side=side,
            entry_timestamp=ts_ms - random.randint(1000, 3600000),  # 1s to 1h ago
            entry_price=entry_price,
            quantity=quantity,
            position_side=position_side,
            ts_ms=ts_ms,
        )

    async def calculate_position_pnl(self, position: Position) -> Optional[PositionPnL]:
        """
        Calculate real-time PnL for a position on mock exchange.
        Note: This is a mock implementation for demonstration.
        """
        try:
            # Get current market price
            quote = await self.get_best_bid_ask(position.pair)
            current_price = quote.mid  # Use mid price for PnL calculation
            mark_price = current_price  # For spot, mark price = current price
            
            # Calculate unrealized PnL
            if position.position_side == "long":
                # Long position: profit when price goes up
                unrealized_pnl = (current_price - position.entry_price) * position.quantity
            else:
                # Short position: profit when price goes down
                unrealized_pnl = (position.entry_price - current_price) * position.quantity
            
            # Calculate PnL percentage
            position_value = position.entry_price * position.quantity
            unrealized_pnl_pct = (unrealized_pnl / position_value) * 100 if position_value > 0 else 0
            
            return PositionPnL(
                position=position,
                current_price=current_price,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
                mark_price=mark_price,
                ts_ms=int(time.time() * 1000),
            )
        except Exception as e:
            # Return None if unable to calculate PnL
            return None 