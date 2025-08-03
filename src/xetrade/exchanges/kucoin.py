# src/xetrade/exchanges/kucoin.py
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

BASE_URL = "https://api.kucoin.com"

@register_exchange
class KuCoin(BaseExchange):
    """
    KuCoin adapter:
      - Best bid/ask: /api/v1/market/orderbook/level1
      - L2 order book: /api/v1/market/orderbook/level2
      - Funding (perps): /api/v1/contracts/funding-rates
    Notes:
      * Funding interval on KuCoin perps is typically 8 hours.
      * KuCoin uses 'BTC-USDT' format for symbols.
    """
    name = "kucoin"
    funding_interval_hours = 8.0
    supports_funding = True

    # ---- symbol formatting ----
    def format_symbol(self, pair: Pair) -> str:
        p = normalize_pair(pair)
        # KuCoin expects 'BTC-USDT'
        return f"{p.base}-{p.quote}"

    # ---- market data ----
    async def get_best_bid_ask(self, pair: Pair) -> Quote:
        sym = self.format_symbol(pair)
        url = f"{BASE_URL}/api/v1/market/orderbook/level1"
        data = await get_json(url, params={"symbol": sym})
        # data: {"code":"200000","data":{"time":1700000000000,"sequence":"123","price":"50000","size":"0.1","bestBid":"49999","bestBidSize":"0.1","bestAsk":"50001","bestAskSize":"0.1"}}
        if data.get("code") != "200000":
            raise RuntimeError(f"KuCoin API error: {data.get('msg', 'Unknown error')}")
        
        ticker_data = data["data"]
        ts_ms = int(ticker_data.get("time", time.time() * 1000))
        return Quote(
            bid=float(ticker_data["bestBid"]), 
            ask=float(ticker_data["bestAsk"]), 
            ts_ms=ts_ms
        )

    async def get_l2_orderbook(self, pair: Pair, depth: int = 100) -> OrderBook:
        sym = self.format_symbol(pair)
        # KuCoin supports depth limits: 20,100
        limit = max(20, min(depth, 100))
        url = f"{BASE_URL}/api/v1/market/orderbook/level2"
        data = await get_json(url, params={"symbol": sym})
        
        if data.get("code") != "200000":
            raise RuntimeError(f"KuCoin API error: {data.get('msg', 'Unknown error')}")
        
        book_data = data["data"]
        # bids/asks are lists of ["price","qty"]
        bids_raw: List[Tuple[float, float]] = [(float(p), float(q)) for p, q in book_data.get("bids", [])]
        asks_raw: List[Tuple[float, float]] = [(float(p), float(q)) for p, q in book_data.get("asks", [])]
        
        bids = [Level(price=p, qty=q) for p, q in bids_raw]
        asks = [Level(price=p, qty=q) for p, q in asks_raw]
        
        ts_ms = int(book_data.get("time", time.time() * 1000))
        ob = OrderBook(bids=bids, asks=asks, ts_ms=ts_ms)
        return sort_l2(ob)

    # ---- funding (perps) ----
    async def get_funding_live_predicted(self, pair: Pair) -> FundingSnapshot:
        """
        KuCoin publishes current funding rate on /api/v1/contracts/funding-rates.
        """
        sym = self.format_symbol(pair)
        url = f"{BASE_URL}/api/v1/contracts/funding-rates"
        data = await get_json(url, params={"symbol": sym})
        
        if data.get("code") != "200000":
            raise RuntimeError(f"KuCoin API error: {data.get('msg', 'Unknown error')}")
        
        if not data.get("data"):
            raise RuntimeError(f"No funding data returned for {sym}")
        
        funding_data = data["data"][0]
        cur = float(funding_data.get("fundingRate", 0.0))
        # KuCoin doesn't provide predicted rate, so we use current as placeholder
        predicted = cur
        ts_ms = int(funding_data.get("time", time.time() * 1000))
        
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
        sym = self.format_symbol(pair)
        url = f"{BASE_URL}/api/v1/contracts/funding-rates"
        out: FundingSeries = []
        
        # Pagination loop
        current_start = start_ms
        while current_start < end_ms:
            params = {
                "symbol": sym, 
                "startAt": current_start, 
                "endAt": end_ms, 
                "limit": 100  # KuCoin max limit
            }
            data = await get_json(url, params=params)
            
            if data.get("code") != "200000":
                raise RuntimeError(f"KuCoin API error: {data.get('msg', 'Unknown error')}")
            
            if not data.get("data"):  # No more data
                break
                
            for row in data.get("data", []):
                # row: {'symbol':'BTC-USDT','fundingRate':'0.0001','time':1700000000000}
                rate = float(row.get("fundingRate", 0.0))
                ts = int(row.get("time"))
                out.append(FundingPoint(ts_ms=ts, rate=rate))
            
            # Update start time for next page
            if data.get("data"):
                last_ts = int(data["data"][-1].get("time", current_start))
                if last_ts <= current_start:  # No progress, avoid infinite loop
                    break
                current_start = last_ts + 1
            else:
                break
                
        return out 