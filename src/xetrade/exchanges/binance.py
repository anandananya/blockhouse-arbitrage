# src/xetrade/exchanges/binance.py
from __future__ import annotations

import time
from typing import List, Tuple

from xetrade.exchanges.base import (
    BaseExchange,
    register_exchange,
    FundingNotSupported,
    normalize_pair,
)
from xetrade.models import Pair, Quote, OrderBook, FundingSnapshot, FundingPoint, FundingSeries, Level
from xetrade.models import to_levels, sort_l2
from xetrade.utils.http import get_json

SPOT_BASE = "https://api.binance.com"
FUTURES_BASE = "https://fapi.binance.com"  # USDT-M perpetuals

@register_exchange
class Binance(BaseExchange):
    """
    Binance adapter:
      - Best bid/ask: /api/v3/ticker/bookTicker
      - L2 order book: /api/v3/depth
      - Funding (perps): /fapi/v1/premiumIndex (snapshot-ish), /fapi/v1/fundingRate (history)
    Notes:
      * Funding interval on Binance perps is typically 8 hours.
      * Binance spot endpoints don’t return a timestamp with bookTicker; we stamp locally.
    """
    name = "binance"
    funding_interval_hours = 8.0

    # ---- symbol formatting ----
    def format_symbol(self, pair: Pair) -> str:
        p = normalize_pair(pair)
        # Binance expects 'BTCUSDT'
        return f"{p.base}{p.quote}"

    # ---- market data ----
    async def get_best_bid_ask(self, pair: Pair) -> Quote:
        sym = self.format_symbol(pair)
        url = f"{SPOT_BASE}/api/v3/ticker/bookTicker"
        data = await get_json(url, params={"symbol": sym})
        # data: {'symbol': 'BTCUSDT','bidPrice':'...','bidQty':'...','askPrice':'...','askQty':'...'}
        ts_ms = int(time.time() * 1000)
        return Quote(bid=float(data["bidPrice"]), ask=float(data["askPrice"]), ts_ms=ts_ms)

    async def get_l2_orderbook(self, pair: Pair, depth: int = 100) -> OrderBook:
        sym = self.format_symbol(pair)
        # Binance spot supports depth limits: 5,10,20,50,100,500,1000,5000
        limit = max(5, min(depth, 1000))
        url = f"{SPOT_BASE}/api/v3/depth"
        data = await get_json(url, params={"symbol": sym, "limit": limit})
        # bids/asks are lists of ["price","qty"]
        bids_raw: List[Tuple[float, float]] = [(float(p), float(q)) for p, q in data.get("bids", [])]
        asks_raw: List[Tuple[float, float]] = [(float(p), float(q)) for p, q in data.get("asks", [])]
        bids = [Level(price=p, qty=q) for p, q in bids_raw]
        asks = [Level(price=p, qty=q) for p, q in asks_raw]
        ob = OrderBook(bids=bids, asks=asks, ts_ms=data.get("lastUpdateId", int(time.time() * 1000)))
        return sort_l2(ob)

    # ---- funding (perps) ----
    async def get_funding_live_predicted(self, pair: Pair) -> FundingSnapshot:
        """
        Binance publishes the most recent funding rate and next funding time on /fapi/v1/premiumIndex.
        Some SDKs expose a “predicted” value; if not present, we echo current as a conservative placeholder.
        """
        sym = self.format_symbol(pair)
        url = f"{FUTURES_BASE}/fapi/v1/premiumIndex"
        data = await get_json(url, params={"symbol": sym})
        # Typical fields: lastFundingRate, nextFundingTime, time
        cur = float(data.get("lastFundingRate", 0.0))
        # If Binance exposes a predicted field in your environment, prefer it; otherwise reuse current.
        predicted = float(data.get("predictedFundingRate", cur)) if "predictedFundingRate" in data else cur
        ts_ms = int(data.get("time", time.time() * 1000))
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
        sym = self.format_symbol(pair)
        url = f"{FUTURES_BASE}/fapi/v1/fundingRate"
        # Binance max limit is 1000 per call. Callers can loop if they need more.
        params = {"symbol": sym, "startTime": start_ms, "endTime": end_ms, "limit": 1000}
        data = await get_json(url, params=params)
        out: FundingSeries = []
        for row in data:
            # row: {'symbol':'BTCUSDT','fundingRate':'0.0001','fundingTime': 1700000000000, ...}
            rate = float(row.get("fundingRate", 0.0))
            ts = int(row.get("fundingTime"))
            out.append(FundingPoint(ts_ms=ts, rate=rate))
        return out
