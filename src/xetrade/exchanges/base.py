# src/exchanges/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterable, List, Tuple, Dict, Type
from xetrade.models import Pair, Quote, OrderBook, FundingSnapshot, FundingSeries

# Common errors
class ExchangeError(Exception): ...
class SymbolError(ExchangeError): ...
class RateLimitError(ExchangeError): ...
class FundingNotSupported(ExchangeError): ...

def normalize_pair(pair: Pair) -> Pair:
    """Uppercase and strip; override per-exchange if needed."""
    return Pair(pair.base.upper(), pair.quote.upper())

class BaseExchange(ABC):
    """
    All concrete exchanges must implement these async methods.
    Keep return types in xetrade.models.
    """
    name: str  # short id like "binance", "okx"

    def __init__(self, *, api_key: str | None = None, api_secret: str | None = None, timeout: float = 10.0):
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout

    # --- Market data ---
    @abstractmethod
    async def get_best_bid_ask(self, pair: Pair) -> Quote:
        """Return best bid/ask for the pair."""
        raise NotImplementedError

    @abstractmethod
    async def get_l2_orderbook(self, pair: Pair, depth: int = 100) -> OrderBook:
        """Return L2 book with bids desc and asks asc."""
        raise NotImplementedError

    # --- Funding (perps) ---
    async def get_funding_live_predicted(self, pair: Pair) -> FundingSnapshot:
        """Current and predicted next funding for the perp."""
        raise FundingNotSupported(f"{self.name} does not support funding")

    async def get_funding_history(self, pair: Pair, start_ms: int, end_ms: int) -> FundingSeries:
        """Historical funding points in [start_ms, end_ms]."""
        raise FundingNotSupported(f"{self.name} does not support funding")

    # --- Helpers overridable per exchange ---
    def format_symbol(self, pair: Pair) -> str:
        """
        Default: BINANCE-style 'BTCUSDT'.
        Override if the API expects 'BTC-USDT' or 'BTC_USDT'.
        """
        p = normalize_pair(pair)
        return f"{p.base}{p.quote}"

# -------- Registry for easy wiring (used by CLI/services) --------

_EXCHANGE_REGISTRY: Dict[str, Type[BaseExchange]] = {}

def register_exchange(cls: Type[BaseExchange]) -> Type[BaseExchange]:
    """Decorator to register exchanges by their .name."""
    if not getattr(cls, "name", None):
        raise ValueError("Exchange class must define a non-empty 'name'")
    _EXCHANGE_REGISTRY[cls.name] = cls
    return cls

def available_exchanges() -> List[str]:
    return sorted(_EXCHANGE_REGISTRY.keys())

def make_exchanges(names: Iterable[str], **kwargs) -> List[BaseExchange]:
    out: List[BaseExchange] = []
    for n in names:
        cls = _EXCHANGE_REGISTRY.get(n.lower())
        if not cls:
            raise ValueError(f"Unknown exchange '{n}'. Known: {', '.join(available_exchanges())}")
        out.append(cls(**kwargs))
    return out
