# src/xetrade/exchanges/derive.py
from __future__ import annotations

import time
from typing import List, Tuple

from xetrade.exchanges.base import (
    BaseExchange,
    register_exchange,
    normalize_pair,
)
from xetrade.models import Pair, Quote, OrderBook, FundingSnapshot, FundingPoint, FundingSeries, Level
from xetrade.models import to_levels, sort_l2
from xetrade.utils.http import get_json

BASE_URL = "https://api.dydx.exchange"

@register_exchange
class Derive(BaseExchange):
    """
    Derive (dYdX) adapter:
      - Best bid/ask: /v3/orderbooks/{market}
      - L2 order book: /v3/orderbooks/{market}
      - Funding (perps): /v3/funding-rates/{market}
    Notes:
      * dYdX is a decentralized exchange with perpetual futures.
      * dYdX uses 'BTC-USD' format for symbols.
      * Funding interval on dYdX perps is typically 1 hour.
    """
    name = "derive"
    funding_interval_hours = 1.0
    supports_funding = True

    # ---- symbol formatting ----
    def format_symbol(self, pair: Pair) -> str:
        p = normalize_pair(pair)
        # dYdX expects 'BTC-USD' format, convert USDT to USD
        if p.quote == "USDT":
            quote = "USD"
        else:
            quote = p.quote
        return f"{p.base}-{quote}"

    # ---- market data ----
    async def get_best_bid_ask(self, pair: Pair) -> Quote:
        sym = self.format_symbol(pair)
        url = f"{BASE_URL}/v3/orderbooks/{sym}"
        data = await get_json(url)
        # data: {"orderbooks":{"BTC-USD":{"bids":[{"price":"50000","size":"0.1"}],"asks":[{"price":"50001","size":"0.1"}]}}}
        if "orderbooks" not in data or sym not in data["orderbooks"]:
            raise RuntimeError(f"No orderbook data returned for {sym}")
        
        book_data = data["orderbooks"][sym]
        bids = book_data.get("bids", [])
        asks = book_data.get("asks", [])
        
        if not bids or not asks:
            raise RuntimeError(f"Insufficient orderbook data for {sym}")
        
        best_bid = float(bids[0]["price"])
        best_ask = float(asks[0]["price"])
        ts_ms = int(time.time() * 1000)  # dYdX doesn't provide timestamp in this endpoint
        
        return Quote(bid=best_bid, ask=best_ask, ts_ms=ts_ms)

    async def get_l2_orderbook(self, pair: Pair, depth: int = 100) -> OrderBook:
        sym = self.format_symbol(pair)
        url = f"{BASE_URL}/v3/orderbooks/{sym}"
        data = await get_json(url)
        
        if "orderbooks" not in data or sym not in data["orderbooks"]:
            raise RuntimeError(f"No orderbook data returned for {sym}")
        
        book_data = data["orderbooks"][sym]
        # bids/asks are lists of {"price":"...","size":"..."}
        bids_raw: List[Tuple[float, float]] = [(float(b["price"]), float(b["size"])) for b in book_data.get("bids", [])]
        asks_raw: List[Tuple[float, float]] = [(float(a["price"]), float(a["size"])) for a in book_data.get("asks", [])]
        
        # Limit to requested depth
        bids_raw = bids_raw[:depth]
        asks_raw = asks_raw[:depth]
        
        bids = [Level(price=p, qty=q) for p, q in bids_raw]
        asks = [Level(price=p, qty=q) for p, q in asks_raw]
        
        ts_ms = int(time.time() * 1000)  # dYdX doesn't provide timestamp in this endpoint
        ob = OrderBook(bids=bids, asks=asks, ts_ms=ts_ms)
        return sort_l2(ob)

    # ---- funding (perps) ----
    async def get_funding_live_predicted(self, pair: Pair) -> FundingSnapshot:
        """
        dYdX publishes current funding rate on /v3/funding-rates/{market}.
        """
        sym = self.format_symbol(pair)
        url = f"{BASE_URL}/v3/funding-rates/{sym}"
        data = await get_json(url)
        
        if "fundingRates" not in data or sym not in data["fundingRates"]:
            raise RuntimeError(f"No funding data returned for {sym}")
        
        funding_data = data["fundingRates"][sym]
        cur = float(funding_data.get("rate", 0.0))
        # dYdX doesn't provide predicted rate, so we use current as placeholder
        predicted = cur
        ts_ms = int(time.time() * 1000)  # dYdX doesn't provide timestamp in this endpoint
        
        return FundingSnapshot(
            current_rate=cur,
            predicted_next_rate=predicted,
            interval_hours=self.funding_interval_hours,
            ts_ms=ts_ms,
        )

    async def get_funding_history(self, pair: Pair, start_ms: int, end_ms: int) -> FundingSeries:
        """
        Historical funding rates for the perpetual swap.
        Note: dYdX public API doesn't provide historical funding data.
        Returns empty list to be explicit about the limitation.
        """
        # dYdX doesn't provide historical funding data in their public API
        # Return empty list to be explicit about this limitation
        return [] 