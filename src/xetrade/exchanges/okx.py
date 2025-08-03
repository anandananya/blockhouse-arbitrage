# src/xetrade/exchanges/okx.py
from __future__ import annotations

import time
from typing import List, Tuple, Optional

from xetrade.exchanges.base import (
    BaseExchange,
    register_exchange,
    normalize_pair,
)
from xetrade.models import (
    Pair, Quote, OrderBook, FundingSnapshot, FundingPoint, FundingSeries, Level,
    OrderRequest, OrderResponse, OrderStatusResponse, CancelResponse, OrderStatus,
    Position, PositionPnL
)
from xetrade.models import to_levels, sort_l2
from xetrade.utils.http import get_json

BASE_URL = "https://www.okx.com"

@register_exchange
class OKX(BaseExchange):
    """
    OKX adapter:
      - Best bid/ask: /api/v5/market/ticker
      - L2 order book: /api/v5/market/books
      - Funding (perps): /api/v5/public/funding-rate
    Notes:
      * Funding interval on OKX perps is typically 8 hours.
      * OKX uses 'BTC-USDT' format for symbols.
    """
    name = "okx"
    funding_interval_hours = 8.0
    supports_funding = True
    supports_trading = True

    # ---- symbol formatting ----
    def format_symbol(self, pair: Pair) -> str:
        p = normalize_pair(pair)
        # OKX expects 'BTC-USDT'
        return f"{p.base}-{p.quote}"

    # ---- market data ----
    async def get_best_bid_ask(self, pair: Pair) -> Quote:
        sym = self.format_symbol(pair)
        url = f"{BASE_URL}/api/v5/market/ticker"
        data = await get_json(url, params={"instId": sym})
        # data: {"code":"0","msg":"","data":[{"instId":"BTC-USDT","last":"...","lastSz":"...","askPx":"...","askSz":"...","bidPx":"...","bidSz":"...","open24h":"...","high24h":"...","low24h":"...","volCcy24h":"...","vol24h":"...","ts":"..."}]}
        if not data.get("data"):
            raise RuntimeError(f"No data returned for {sym}")
        
        ticker = data["data"][0]
        ts_ms = int(ticker.get("ts", time.time() * 1000))
        return Quote(
            bid=float(ticker["bidPx"]), 
            ask=float(ticker["askPx"]), 
            ts_ms=ts_ms
        )

    async def get_l2_orderbook(self, pair: Pair, depth: int = 100) -> OrderBook:
        sym = self.format_symbol(pair)
        # OKX supports depth limits: 1,5,20,100,400
        limit = max(1, min(depth, 400))
        url = f"{BASE_URL}/api/v5/market/books"
        data = await get_json(url, params={"instId": sym, "sz": limit})
        
        if not data.get("data"):
            raise RuntimeError(f"No orderbook data returned for {sym}")
        
        book_data = data["data"][0]
        # bids/asks are lists of ["price","qty","num_orders","level"]
        bids_raw: List[Tuple[float, float]] = [(float(p), float(q)) for p, q, _, _ in book_data.get("bids", [])]
        asks_raw: List[Tuple[float, float]] = [(float(p), float(q)) for p, q, _, _ in book_data.get("asks", [])]
        
        bids = [Level(price=p, qty=q) for p, q in bids_raw]
        asks = [Level(price=p, qty=q) for p, q in asks_raw]
        
        ts_ms = int(book_data.get("ts", time.time() * 1000))
        ob = OrderBook(bids=bids, asks=asks, ts_ms=ts_ms)
        return sort_l2(ob)

    # ---- funding (perps) ----
    async def get_funding_live_predicted(self, pair: Pair) -> FundingSnapshot:
        """
        OKX publishes current funding rate on /api/v5/public/funding-rate.
        """
        p = normalize_pair(pair)
        # For funding rates, OKX expects perpetual futures symbols like 'BTC-USDT-SWAP'
        sym = f"{p.base}-{p.quote}-SWAP"
        url = f"{BASE_URL}/api/v5/public/funding-rate"
        data = await get_json(url, params={"instId": sym})
        
        if not data.get("data"):
            raise RuntimeError(f"No funding data returned for {sym}")
        
        funding_data = data["data"][0]
        cur = float(funding_data.get("fundingRate", 0.0))
        # OKX doesn't provide predicted rate, so we use current as placeholder
        predicted = cur
        ts_ms = int(funding_data.get("ts", time.time() * 1000))
        
        return FundingSnapshot(
            current_rate=cur,
            predicted_next_rate=predicted,
            interval_hours=self.funding_interval_hours,
            ts_ms=ts_ms,
        )

    async def get_funding_history(self, pair: Pair, start_ms: int, end_ms: int) -> FundingSeries:
        """
        Historical funding rates for the perpetual swap.
        Includes pagination to handle large date ranges.
        """
        p = normalize_pair(pair)
        # For funding rates, OKX expects perpetual futures symbols like 'BTC-USDT-SWAP'
        sym = f"{p.base}-{p.quote}-SWAP"
        url = f"{BASE_URL}/api/v5/public/funding-rate-history"
        out: FundingSeries = []
        
        # Pagination loop
        current_after = start_ms
        while current_after < end_ms:
            params = {
                "instId": sym, 
                "after": current_after, 
                "before": end_ms, 
                "limit": 100  # OKX max limit
            }
            data = await get_json(url, params=params)
            
            if not data.get("data"):  # No more data
                break
                
            for row in data.get("data", []):
                # row: {'instId':'BTC-USDT-SWAP','fundingRate':'0.0001','realizedRate':'0.0001','interestRate':'0.0001','ts':'1700000000000'}
                rate = float(row.get("fundingRate", 0.0))
                ts = int(row.get("ts"))
                out.append(FundingPoint(ts_ms=ts, rate=rate))
            
            # Update after timestamp for next page
            if data.get("data"):
                last_ts = int(data["data"][-1].get("ts", current_after))
                if last_ts <= current_after:  # No progress, avoid infinite loop
                    break
                current_after = last_ts + 1
            else:
                break
                
        return out 

    # ---- trading (order management) ----
    async def place_order(self, request: OrderRequest) -> OrderResponse:
        """
        Place a new order on OKX.
        Note: This is a mock implementation for demonstration.
        In production, you would need API keys and proper authentication.
        """
        sym = self.format_symbol(request.pair)
        ts_ms = int(time.time() * 1000)
        
        # Mock order ID generation
        order_id = f"okx_{ts_ms}_{hash(sym) % 10000}"
        
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
        Cancel an existing order on OKX.
        Note: This is a mock implementation for demonstration.
        """
        ts_ms = int(time.time() * 1000)
        
        # Mock cancellation - in reality, you'd call the OKX API
        # url = f"{BASE_URL}/api/v5/trade/cancel-order"
        # data = await post_json(url, {"ordId": order_id, "instId": self.format_symbol(pair)})
        
        return CancelResponse(
            order_id=order_id,
            venue=self.name,
            success=True,
            message="Order cancelled successfully",
            ts_ms=ts_ms,
        )

    async def get_order_status(self, order_id: str, pair: Pair) -> OrderStatusResponse:
        """
        Get the current status of an order on OKX.
        Note: This is a mock implementation for demonstration.
        """
        ts_ms = int(time.time() * 1000)
        
        # Mock status - in reality, you'd call the OKX API
        # url = f"{BASE_URL}/api/v5/trade/order"
        # data = await get_json(url, {"ordId": order_id, "instId": self.format_symbol(pair)})
        
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
        Get position details from a filled order on OKX.
        Note: This is a mock implementation for demonstration.
        """
        ts_ms = int(time.time() * 1000)
        
        # Mock position creation - in reality, you'd query the exchange API
        # url = f"{BASE_URL}/api/v5/account/positions"
        # data = await get_json(url, {"instId": self.format_symbol(pair)})
        
        # For demonstration, create a mock position from the order ID
        # In reality, you'd need to check if the order was filled and get actual position data
        
        # Extract side from order ID (mock logic)
        import random
        side = random.choice(["buy", "sell"])
        position_side = "long" if side == "buy" else "short"
        
        # Mock entry price and quantity
        entry_price = 50000.0 + random.uniform(-1000, 1000)  # Around $50k
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
        Calculate real-time PnL for a position on OKX.
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