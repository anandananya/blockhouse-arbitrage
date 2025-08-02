# src/xetrade/models.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Literal, Tuple

Side = Literal["buy", "sell"]

# ----- Core domain types -----

@dataclass(frozen=True)
class Pair:
    base: str   # e.g., "BTC"
    quote: str  # e.g., "USDT"

    @staticmethod
    def parse(s: str) -> "Pair":
        """
        Accepts 'BTC-USDT', 'btc_usdt', 'BTCUSDT' (ambiguous for some),
        or ('BTC','USDT')-style strings. Normalizes to upper-case.
        """
        s = s.strip().upper().replace("/", "-").replace("_", "-")
        if "-" in s:
            a, b = s.split("-", 1)
            return Pair(a, b)
        # Fallback: try common quote suffixes
        for q in ("USDT", "USD", "USDC", "BTC", "ETH", "EUR"):
            if s.endswith(q) and len(s) > len(q):
                return Pair(s[:-len(q)], q)
        raise ValueError(f"Cannot parse trading pair from '{s}'")

    def human(self) -> str:
        return f"{self.base}-{self.quote}"

    def concat(self) -> str:
        """'BTCUSDT' style (Binance)."""
        return f"{self.base}{self.quote}"


@dataclass(frozen=True)
class Quote:
    bid: float          # best bid price
    ask: float          # best ask price
    ts_ms: int          # exchange timestamp (ms)

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0


@dataclass(frozen=True)
class Level:
    price: float        # price at this level
    qty: float          # base-asset quantity available at this price


@dataclass(frozen=True)
class OrderBook:
    bids: List[Level]   # sorted DESC by price
    asks: List[Level]   # sorted ASC by price
    ts_ms: int

    def best_bid(self) -> float:
        return self.bids[0].price if self.bids else float("nan")

    def best_ask(self) -> float:
        return self.asks[0].price if self.asks else float("nan")

    def mid(self) -> float:
        bb, ba = self.best_bid(), self.best_ask()
        return (bb + ba) / 2.0


# ----- Funding data -----

@dataclass(frozen=True)
class FundingSnapshot:
    """
    Represents funding info around 'now' for a perpetual swap.
    """
    current_rate: float         # e.g., 0.0001 for 0.01%
    predicted_next_rate: float  # exchange-published prediction (if available)
    interval_hours: float       # e.g., 8.0, 4.0, 1.0
    ts_ms: int


@dataclass(frozen=True)
class FundingPoint:
    ts_ms: int
    rate: float                 # funding rate for that period


FundingSeries = List[FundingPoint]


# ----- Small helpers used everywhere -----

def sort_l2(book: OrderBook) -> OrderBook:
    """Ensure canonical sorting (defensive; some APIs don't guarantee)."""
    bids = sorted(book.bids, key=lambda x: x.price, reverse=True)
    asks = sorted(book.asks, key=lambda x: x.price)
    return OrderBook(bids=bids, asks=asks, ts_ms=book.ts_ms)


def to_levels(side: Literal["bid", "ask"], raw: List[Tuple[float, float]]) -> List[Level]:
    """
    Convert a list of [price, qty] into Level[], filtering zero/negatives.
    side only affects expected ordering; we don't sort here.
    """
    out: List[Level] = []
    for p, q in raw:
        if p > 0 and q > 0:
            out.append(Level(price=float(p), qty=float(q)))
    return out
