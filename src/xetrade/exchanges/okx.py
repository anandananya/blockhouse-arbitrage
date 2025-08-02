# src/xetrade/exchanges/okx.py
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
        """
        p = normalize_pair(pair)
        # For funding rates, OKX expects perpetual futures symbols like 'BTC-USDT-SWAP'
        sym = f"{p.base}-{p.quote}-SWAP"
        url = f"{BASE_URL}/api/v5/public/funding-rate-history"
        # OKX max limit is 100 per call
        params = {"instId": sym, "after": start_ms, "before": end_ms, "limit": 100}
        data = await get_json(url, params=params)
        
        out: FundingSeries = []
        for row in data.get("data", []):
            # row: {'instId':'BTC-USDT','fundingRate':'0.0001','realizedRate':'0.0001','interestRate':'0.0001','ts':'1700000000000'}
            rate = float(row.get("fundingRate", 0.0))
            ts = int(row.get("ts"))
            out.append(FundingPoint(ts_ms=ts, rate=rate))
        return out 