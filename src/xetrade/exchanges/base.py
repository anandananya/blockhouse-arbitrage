# src/exchanges/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterable, List, Tuple, Dict, Type
from xetrade.models import (
    Pair, Quote, OrderBook, FundingSnapshot, FundingSeries,
    OrderRequest, OrderResponse, OrderStatusResponse, CancelResponse,
    Position, PositionPnL
)
from xetrade.utils.symbol_mapper import UniversalSymbolMapper

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
    
    # Capability flags for early feature detection
    supports_spot: bool = True
    supports_funding: bool = False
    supports_l2_orderbook: bool = True
    supports_trading: bool = False  # Order placement, cancellation, status

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
        if not self.supports_funding:
            raise FundingNotSupported(f"{self.name} does not support funding")
        raise FundingNotSupported(f"{self.name} does not support funding")

    async def get_funding_history(self, pair: Pair, start_ms: int, end_ms: int) -> FundingSeries:
        """Historical funding points in [start_ms, end_ms]."""
        if not self.supports_funding:
            raise FundingNotSupported(f"{self.name} does not support funding")
        raise FundingNotSupported(f"{self.name} does not support funding")

    # --- Trading (Order Management) ---
    async def place_order(self, request: OrderRequest) -> OrderResponse:
        """Place a new order (LIMIT or MARKET)."""
        if not self.supports_trading:
            raise RuntimeError(f"{self.name} does not support trading")
        raise NotImplementedError

    async def cancel_order(self, order_id: str, pair: Pair) -> CancelResponse:
        """Cancel an existing order."""
        if not self.supports_trading:
            raise RuntimeError(f"{self.name} does not support trading")
        raise NotImplementedError

    async def get_order_status(self, order_id: str, pair: Pair) -> OrderStatusResponse:
        """Get the current status of an order."""
        if not self.supports_trading:
            raise RuntimeError(f"{self.name} does not support trading")
        raise NotImplementedError

    # --- Position Monitoring ---
    async def get_position_from_order(self, order_id: str, pair: Pair) -> Optional[Position]:
        """
        Get position details from a filled order.
        Returns None if order is not filled or position not found.
        """
        if not self.supports_trading:
            raise RuntimeError(f"{self.name} does not support trading")
        raise NotImplementedError

    async def calculate_position_pnl(self, position: Position) -> Optional[PositionPnL]:
        """
        Calculate real-time PnL for a position.
        Returns None if unable to calculate (e.g., no current price).
        """
        if not self.supports_trading:
            raise RuntimeError(f"{self.name} does not support trading")
        raise NotImplementedError

    # --- Helpers overridable per exchange ---
    def format_symbol(self, pair: Pair) -> str:
        """
        Default: BINANCE-style 'BTCUSDT'.
        Override if the API expects 'BTC-USDT' or 'BTC_USDT'.
        """
        p = normalize_pair(pair)
        return f"{p.base}{p.quote}"
    
    def get_universal_symbol(self, exchange_symbol: str) -> str:
        """
        Convert exchange-specific symbol to universal format.
        """
        mapper = UniversalSymbolMapper()
        return mapper.normalize_symbol(exchange_symbol, self.name)
    
    def get_exchange_symbol(self, universal_symbol: str) -> str:
        """
        Convert universal symbol to exchange-specific format.
        """
        mapper = UniversalSymbolMapper()
        return mapper.get_exchange_symbol(universal_symbol, self.name)

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
