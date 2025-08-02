# src/services/price_impact.py
from __future__ import annotations
from typing import Tuple
from xetrade.models import OrderBook, Side

def walk_book(book: OrderBook, side: Side, trade_volume_quote: float) -> Tuple[float, float]:
    """
    Simulate filling a market order of size 'trade_volume_quote' (in quote currency).
    Returns (avg_execution_price, filled_base_qty).

    For buys we consume asks from lowest up.
    For sells we consume bids from highest down.
    """
    if trade_volume_quote <= 0:
        raise ValueError("trade_volume_quote must be > 0")

    levels = book.asks if side == "buy" else book.bids

    remaining_q = float(trade_volume_quote)
    spent_q = 0.0         # total quote spent/received
    filled_base = 0.0     # total base acquired/sold

    for lvl in levels:
        level_cap_q = lvl.price * lvl.qty  # quote capacity at this level
        take_q = min(remaining_q, level_cap_q)
        if take_q <= 0:
            continue
        base_taken = take_q / lvl.price

        spent_q += take_q
        filled_base += base_taken
        remaining_q -= take_q

        if remaining_q <= 1e-12:
            break

    if filled_base == 0.0:
        # book too thin for requested size
        return float("nan"), 0.0

    avg_exec = spent_q / filled_base
    return avg_exec, filled_base


def price_impact_pct(book: OrderBook, side: Side, trade_volume_quote: float) -> float:
    """
    Computes % impact relative to mid-price:
        (avg_exec - mid) / mid * 100
    Positive means worse than mid (more expensive for buys, cheaper for sells).
    """
    avg_exec, filled_base = walk_book(book, side, trade_volume_quote)
    if filled_base == 0.0 or avg_exec != avg_exec:  # NaN guard
        return float("nan")
    mid = book.mid()
    if mid <= 0:
        return float("nan")
    return (avg_exec - mid) / mid * 100.0
