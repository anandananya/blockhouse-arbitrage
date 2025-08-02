# src/services/funding.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from xetrade.models import FundingPoint, FundingSeries, FundingSnapshot

# --- Core math helpers ---

def periods_per_day(interval_hours: float) -> float:
    if interval_hours <= 0:
        raise ValueError("interval_hours must be > 0")
    return 24.0 / interval_hours

def apr_from_periodic(rate: float, interval_hours: float) -> float:
    """
    Convert a single funding rate for one period into APR (simple, non-compounded).
    Example: rate=0.0001 (0.01%) every 8h => APR ≈ 0.0001 * (24/8) * 365
    """
    return rate * periods_per_day(interval_hours) * 365.0

def apy_from_periodic(rate: float, interval_hours: float) -> float:
    """
    Convert a single funding rate to APY (compounded each period).
    """
    n = periods_per_day(interval_hours) * 365.0
    return (1.0 + rate) ** n - 1.0

def daily_return_from_periodic(rate: float, interval_hours: float) -> float:
    """
    Effective daily return from a per-period rate (compounded within the day).
    """
    n = periods_per_day(interval_hours)
    return (1.0 + rate) ** n - 1.0

# --- Snapshot utilities ---

@dataclass(frozen=True)
class FundingAPR:
    """Convenient rolled-up view of a snapshot."""
    current_rate: float
    predicted_next_rate: float
    interval_hours: float
    current_apr: float
    predicted_next_apr: float
    current_apy: float
    predicted_next_apy: float
    daily_return: float
    ts_ms: int

def summarize_snapshot(s: FundingSnapshot) -> FundingAPR:
    cur_apr = apr_from_periodic(s.current_rate, s.interval_hours)
    nxt_apr = apr_from_periodic(s.predicted_next_rate, s.interval_hours)
    cur_apy = apy_from_periodic(s.current_rate, s.interval_hours)
    nxt_apy = apy_from_periodic(s.predicted_next_rate, s.interval_hours)
    daily = daily_return_from_periodic(s.current_rate, s.interval_hours)
    return FundingAPR(
        current_rate=s.current_rate,
        predicted_next_rate=s.predicted_next_rate,
        interval_hours=s.interval_hours,
        current_apr=cur_apr,
        predicted_next_apr=nxt_apr,
        current_apy=cur_apy,
        predicted_next_apy=nxt_apy,
        daily_return=daily,
        ts_ms=s.ts_ms,
    )

# --- History utilities ---

@dataclass(frozen=True)
class FundingHistorySummary:
    """
    Aggregates a sequence of historical funding points that are assumed to be
    one-per-period for a constant interval (e.g., every 8h).
    """
    interval_hours: float
    count: int
    sum_rates: float
    mean_rate_per_period: float
    mean_apr: float
    mean_apy: float

def summarize_history(series: FundingSeries, interval_hours: float) -> FundingHistorySummary:
    if not series:
        return FundingHistorySummary(interval_hours, 0, 0.0, float("nan"), float("nan"), float("nan"))
    total = sum(p.rate for p in series)
    mean_periodic = total / len(series)
    mean_apr = apr_from_periodic(mean_periodic, interval_hours)
    mean_apy = apy_from_periodic(mean_periodic, interval_hours)
    return FundingHistorySummary(
        interval_hours=interval_hours,
        count=len(series),
        sum_rates=total,
        mean_rate_per_period=mean_periodic,
        mean_apr=mean_apr,
        mean_apy=mean_apy,
    )

# --- Convenience transformers ---

def to_apr_series(series: FundingSeries, interval_hours: float) -> List[Tuple[int, float]]:
    """
    Convert a FundingSeries to [(ts_ms, apr_value), ...]
    """
    out: List[Tuple[int, float]] = []
    for p in series:
        out.append((p.ts_ms, apr_from_periodic(p.rate, interval_hours)))
    return out

def to_apy_series(series: FundingSeries, interval_hours: float) -> List[Tuple[int, float]]:
    out: List[Tuple[int, float]] = []
    for p in series:
        out.append((p.ts_ms, apy_from_periodic(p.rate, interval_hours)))
    return out
