# src/services/aggregator.py
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from xetrade.models import Pair, Quote
from xetrade.exchanges.base import BaseExchange

@dataclass(frozen=True)
class VenueQuote:
    venue: str
    quote: Quote

async def best_on_venue(ex: BaseExchange, pair: Pair) -> VenueQuote:
    q = await ex.get_best_bid_ask(pair)
    return VenueQuote(ex.name, q)

async def gather_quotes(exchanges: Iterable[BaseExchange], pair: Pair) -> List[VenueQuote]:
    tasks = [asyncio.create_task(best_on_venue(ex, pair)) for ex in exchanges]
    results: List[VenueQuote] = []
    for t in asyncio.as_completed(tasks):
        try:
            results.append(await t)
        except Exception:
            # You might log errors per venue here; we skip failed venues
            pass
    return results

def select_best(quotes: List[VenueQuote]) -> Tuple[Optional[VenueQuote], Optional[VenueQuote]]:
    """
    Returns (best_bid_venue_quote, best_ask_venue_quote).
    - best bid = highest bid price
    - best ask = lowest ask price
    """
    if not quotes:
        return None, None
    best_bid = max(quotes, key=lambda vq: vq.quote.bid, default=None)
    best_ask = min(quotes, key=lambda vq: vq.quote.ask, default=None)
    return best_bid, best_ask

async def best_across_venues(exchanges: Iterable[BaseExchange], pair: Pair):
    """
    Convenience: fetch all, then return a dict:
      {
        "best_bid": {"venue": ..., "price": ...},
        "best_ask": {"venue": ..., "price": ...},
        "mid": float,
        "all": [VenueQuote, ...]
      }
    """
    vqs = await gather_quotes(exchanges, pair)
    bid_vq, ask_vq = select_best(vqs)
    if not bid_vq or not ask_vq:
        return {"best_bid": None, "best_ask": None, "mid": None, "all": vqs}
    mid = (bid_vq.quote.bid + ask_vq.quote.ask) / 2.0
    return {
        "best_bid": {"venue": bid_vq.venue, "price": bid_vq.quote.bid, "ts_ms": bid_vq.quote.ts_ms},
        "best_ask": {"venue": ask_vq.venue, "price": ask_vq.quote.ask, "ts_ms": ask_vq.quote.ts_ms},
        "mid": mid,
        "all": vqs,
    }
