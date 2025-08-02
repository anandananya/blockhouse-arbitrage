# src/xetrade/exchanges/bitmart.py
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

BASE_URL = "https://api-cloud.bitmart.com"

@register_exchange
class Bitmart(BaseExchange):
    """
    Bitmart adapter:
      - Best bid/ask: /spot/v1/ticker
      - L2 order book: /spot/v1/symbols/book
      - Funding (perps): Not supported (spot only)
    Notes:
      * Bitmart is primarily a spot exchange, no perpetual futures.
      * Bitmart uses 'BTC_USDT' format for symbols.
    """
    name = "bitmart"
    funding_interval_hours = 8.0

    # ---- symbol formatting ----
    def format_symbol(self, pair: Pair) -> str:
        p = normalize_pair(pair)
        # Bitmart expects 'BTC_USDT'
        return f"{p.base}_{p.quote}"

    # ---- market data ----
    async def get_best_bid_ask(self, pair: Pair) -> Quote:
        sym = self.format_symbol(pair)
        url = f"{BASE_URL}/spot/v1/ticker"
        data = await get_json(url, params={"symbol": sym})
        # data: {"message":"OK","code":1000,"trace":"...","data":{"symbol":"BTC_USDT","last_price":"50000","quote_volume_24h":"1000000","base_volume_24h":"20","high_24h":"51000","low_24h":"49000","open_24h":"49500","close_24h":"50000","best_ask":"50001","best_ask_size":"0.1","best_bid":"49999","best_bid_size":"0.1","fluctuation":"0.01","url":"..."}}
        if data.get("code") != 1000:
            raise RuntimeError(f"Bitmart API error: {data.get('message', 'Unknown error')}")
        
        ticker_data = data["data"]
        ts_ms = int(time.time() * 1000)  # Bitmart doesn't provide timestamp
        return Quote(
            bid=float(ticker_data["best_bid"]), 
            ask=float(ticker_data["best_ask"]), 
            ts_ms=ts_ms
        )

    async def get_l2_orderbook(self, pair: Pair, depth: int = 100) -> OrderBook:
        sym = self.format_symbol(pair)
        # Bitmart supports depth limits: 5,15,50,100,200,500
        limit = max(5, min(depth, 500))
        url = f"{BASE_URL}/spot/v1/symbols/book"
        data = await get_json(url, params={"symbol": sym, "precision": 8, "size": limit})
        
        if data.get("code") != 1000:
            raise RuntimeError(f"Bitmart API error: {data.get('message', 'Unknown error')}")
        
        book_data = data["data"]
        # bids/asks are lists of ["price","qty"]
        bids_raw: List[Tuple[float, float]] = [(float(p), float(q)) for p, q in book_data.get("bids", [])]
        asks_raw: List[Tuple[float, float]] = [(float(p), float(q)) for p, q in book_data.get("asks", [])]
        
        bids = [Level(price=p, qty=q) for p, q in bids_raw]
        asks = [Level(price=p, qty=q) for p, q in asks_raw]
        
        ts_ms = int(time.time() * 1000)  # Bitmart doesn't provide timestamp
        ob = OrderBook(bids=bids, asks=asks, ts_ms=ts_ms)
        return sort_l2(ob)

    # ---- funding (perps) ----
    async def get_funding_live_predicted(self, pair: Pair) -> FundingSnapshot:
        """
        Bitmart is primarily a spot exchange and doesn't support perpetual futures.
        """
        raise RuntimeError("Bitmart does not support perpetual futures funding rates")

    async def get_funding_history(self, pair: Pair, start_ms: int, end_ms: int) -> FundingSeries:
        """
        Bitmart is primarily a spot exchange and doesn't support perpetual futures.
        """
        raise RuntimeError("Bitmart does not support perpetual futures funding rates") 