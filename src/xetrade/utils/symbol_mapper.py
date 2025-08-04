# src/xetrade/utils/symbol_mapper.py
from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

class QuoteCurrencyType(Enum):
    """Types of quote currencies for classification."""
    USD = "USD"           # US Dollar
    USDT = "USDT"         # Tether USD
    USDC = "USDC"         # USD Coin
    BUSD = "BUSD"         # Binance USD
    DAI = "DAI"           # Dai Stablecoin
    EUR = "EUR"           # Euro
    GBP = "GBP"           # British Pound
    BTC = "BTC"           # Bitcoin
    ETH = "ETH"           # Ethereum
    OTHER = "OTHER"       # Other cryptocurrencies

@dataclass(frozen=True)
class SymbolMapping:
    """Represents a mapping between exchange-specific and universal symbols."""
    exchange_symbol: str
    universal_symbol: str
    base_asset: str
    quote_asset: str
    quote_type: QuoteCurrencyType
    confidence: float  # 0.0 to 1.0, how confident we are in this mapping

class UniversalSymbolMapper:
    """
    Universal symbol mapper for standardizing trading pair symbols across exchanges.
    
    Handles variations in:
    - Prefixes (e.g., 1000BONK vs BONK)
    - Suffixes (e.g., -USD vs -USDT)
    - Quote currency notation (e.g., USD vs USDT vs USDC)
    - Separators (e.g., BTC-USDT vs BTCUSDT vs BTC/USDT)
    """
    
    def __init__(self):
        # Common quote currency mappings
        self.quote_mappings = {
            # USD equivalents
            "USD": QuoteCurrencyType.USD,
            "USDT": QuoteCurrencyType.USDT,
            "USDC": QuoteCurrencyType.USDC,
            "BUSD": QuoteCurrencyType.BUSD,
            "DAI": QuoteCurrencyType.DAI,
            "TUSD": QuoteCurrencyType.USD,  # TrueUSD
            "PAX": QuoteCurrencyType.USD,   # Paxos Standard
            
            # Other fiat
            "EUR": QuoteCurrencyType.EUR,
            "GBP": QuoteCurrencyType.GBP,
            "JPY": QuoteCurrencyType.OTHER,
            "KRW": QuoteCurrencyType.OTHER,
            "CNY": QuoteCurrencyType.OTHER,
            
            # Major cryptocurrencies
            "BTC": QuoteCurrencyType.BTC,
            "ETH": QuoteCurrencyType.ETH,
            "BNB": QuoteCurrencyType.OTHER,
            "SOL": QuoteCurrencyType.OTHER,
            "ADA": QuoteCurrencyType.OTHER,
        }
        
        # Common base asset prefixes/suffixes to strip
        self.prefix_patterns = [
            r"^1000",      # 1000BONK -> BONK
            r"^100",       # 100SHIB -> SHIB
            r"^10",        # 10DOGE -> DOGE
            r"^1",         # 1INCH -> INCH (but be careful)
        ]
        
        # Known asset mappings (exchange-specific to universal)
        self.asset_mappings = {
            # Common variations
            "XBT": "BTC",      # Bitcoin (XBT is sometimes used)
            "BCC": "BCH",      # Bitcoin Cash (old symbol)
            "BCHABC": "BCH",   # Bitcoin Cash ABC
            "BCHSV": "BSV",    # Bitcoin Cash SV
            
            # Stablecoin variations
            "USDT": "USDT",
            "USDC": "USDC",
            "BUSD": "BUSD",
            "DAI": "DAI",
            
            # Meme coins
            "DOGE": "DOGE",
            "SHIB": "SHIB",
            "BONK": "BONK",
            "PEPE": "PEPE",
            "WIF": "WIF",
            
            # DeFi tokens
            "UNI": "UNI",
            "AAVE": "AAVE",
            "COMP": "COMP",
            "LINK": "LINK",
            "MKR": "MKR",
            
            # Layer 1s
            "ETH": "ETH",
            "SOL": "SOL",
            "ADA": "ADA",
            "DOT": "DOT",
            "AVAX": "AVAX",
            "MATIC": "MATIC",
            "ATOM": "ATOM",
            "NEAR": "NEAR",
            "FTM": "FTM",
            "ALGO": "ALGO",
        }
        
        # Exchange-specific symbol patterns
        self.exchange_patterns = {
            "binance": {
                "separator": "",           # BTCUSDT
                "quote_suffix": True,      # USDT suffix
            },
            "okx": {
                "separator": "-",          # BTC-USDT
                "quote_suffix": True,      # USDT suffix
            },
            "kucoin": {
                "separator": "-",          # BTC-USDT
                "quote_suffix": True,      # USDT suffix
            },
            "bitmart": {
                "separator": "_",          # BTC_USDT
                "quote_suffix": True,      # USDT suffix
            },
            "derive": {
                "separator": "-",          # BTC-USD
                "quote_suffix": False,     # USD (not USDT)
            },
        }
    
    def normalize_symbol(self, symbol: str, exchange: str = "unknown") -> str:
        """
        Normalize a symbol to a standard format.
        
        Args:
            symbol: Exchange-specific symbol (e.g., "BTCUSDT", "BTC-USDT")
            exchange: Exchange name for context
            
        Returns:
            Normalized symbol in universal format (e.g., "BTC/USDT")
        """
        # Clean the symbol
        symbol = symbol.strip().upper()
        
        # Handle common separators
        separators = ["-", "_", "/"]
        base, quote = None, None
        
        for sep in separators:
            if sep in symbol:
                parts = symbol.split(sep, 1)
                if len(parts) == 2:
                    base, quote = parts
                    break
        
        # Handle no separator case (e.g., BTCUSDT)
        if not base or not quote:
            base, quote = self._infer_base_quote(symbol)
        
        if not base or not quote:
            # Try to infer from common patterns
            base, quote = self._infer_base_quote(symbol)
        
        if not base or not quote:
            return symbol  # Return original if we can't parse
        
        # Normalize base asset
        base = self._normalize_base_asset(base)
        
        # Normalize quote asset
        quote = self._normalize_quote_asset(quote)
        
        return f"{base}/{quote}"
    
    def _infer_base_quote(self, symbol: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Infer base and quote assets from a symbol without clear separator.
        """
        # Common quote currencies to look for
        quote_currencies = ["USDT", "USD", "USDC", "BTC", "ETH", "EUR", "GBP", "BUSD", "DAI"]
        
        for quote in quote_currencies:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                if base:  # Ensure we have a base asset
                    return base, quote
        
        # Try to find common base assets
        common_bases = ["BTC", "ETH", "SOL", "ADA", "DOT", "AVAX", "MATIC", "ATOM", "NEAR", "FTM", "ALGO"]
        
        for base in common_bases:
            if symbol.startswith(base):
                quote = symbol[len(base):]
                if quote:  # Ensure we have a quote asset
                    return base, quote
        
        return None, None
    
    def _normalize_base_asset(self, base: str) -> str:
        """
        Normalize base asset name.
        """
        # Strip common prefixes
        for pattern in self.prefix_patterns:
            base = re.sub(pattern, "", base)
        
        # Apply known mappings
        return self.asset_mappings.get(base, base)
    
    def _normalize_quote_asset(self, quote: str) -> str:
        """
        Normalize quote asset name.
        """
        # Apply known mappings
        return self.asset_mappings.get(quote, quote)
    
    def get_quote_type(self, quote: str) -> QuoteCurrencyType:
        """Get the quote currency type for classification."""
        return self.quote_mappings.get(quote, QuoteCurrencyType.OTHER)

    def map_symbol(self, exchange_symbol: str, exchange: str = "unknown") -> SymbolMapping:
        """
        Map an exchange-specific symbol to universal format with confidence.
        
        Args:
            exchange_symbol: Exchange-specific symbol
            exchange: Exchange name for context
            
        Returns:
            SymbolMapping with universal symbol and confidence
        """
        universal_symbol = self.normalize_symbol(exchange_symbol, exchange)
        
        # Parse the universal symbol
        if "/" in universal_symbol:
            base, quote = universal_symbol.split("/", 1)
        else:
            base, quote = None, None
        
        # Calculate confidence based on various factors
        confidence = self._calculate_confidence(exchange_symbol, universal_symbol, base, quote, exchange)
        
        return SymbolMapping(
            exchange_symbol=exchange_symbol,
            universal_symbol=universal_symbol,
            base_asset=base or "",
            quote_asset=quote or "",
            quote_type=self.get_quote_type(quote or ""),
            confidence=confidence
        )
    
    def _calculate_confidence(self, exchange_symbol: str, universal_symbol: str, 
                            base: Optional[str], quote: Optional[str], exchange: str) -> float:
        """
        Calculate confidence score for the mapping (0.0 to 1.0).
        """
        confidence = 0.5  # Base confidence
        
        # Bonus for successful parsing
        if base and quote:
            confidence += 0.2
        
        # Bonus for known assets
        if base in self.asset_mappings:
            confidence += 0.1
        if quote in self.asset_mappings:
            confidence += 0.1
        
        # Bonus for known quote types
        quote_type = self.get_quote_type(quote or "")
        if quote_type != QuoteCurrencyType.OTHER:
            confidence += 0.1
        
        # Bonus for exchange-specific patterns
        if exchange in self.exchange_patterns:
            confidence += 0.1
        
        # Penalty for unknown patterns
        if not base or not quote:
            confidence -= 0.3
        
        return max(0.0, min(1.0, confidence))
    
    def find_equivalent_symbols(self, target_symbol: str, exchange_symbols: List[str], 
                              exchange: str = "unknown") -> List[SymbolMapping]:
        """
        Find all symbols that map to the same universal symbol.
        
        Args:
            target_symbol: Target universal symbol (e.g., "BONK/USD")
            exchange_symbols: List of exchange-specific symbols to check
            exchange: Exchange name for context
            
        Returns:
            List of SymbolMapping objects that map to the target
        """
        target_base, target_quote = target_symbol.split("/", 1) if "/" in target_symbol else (None, None)
        
        results = []
        for symbol in exchange_symbols:
            mapping = self.map_symbol(symbol, exchange)
            if mapping.universal_symbol == target_symbol:
                results.append(mapping)
        
        return results
    
    def get_exchange_symbol(self, universal_symbol: str, exchange: str) -> str:
        """
        Convert universal symbol to exchange-specific format.
        
        Args:
            universal_symbol: Universal symbol (e.g., "BTC/USDT")
            exchange: Target exchange
            
        Returns:
            Exchange-specific symbol
        """
        if "/" not in universal_symbol:
            return universal_symbol
        
        base, quote = universal_symbol.split("/", 1)
        
        # Get exchange pattern
        pattern = self.exchange_patterns.get(exchange, {
            "separator": "-",
            "quote_suffix": True
        })
        
        separator = pattern["separator"]
        quote_suffix = pattern["quote_suffix"]
        
        # Apply exchange-specific formatting
        if separator:
            return f"{base}{separator}{quote}"
        else:
            return f"{base}{quote}"
    
    def validate_mapping(self, exchange_symbol: str, expected_universal: str, 
                        exchange: str = "unknown") -> bool:
        """
        Validate that an exchange symbol maps to the expected universal symbol.
        
        Args:
            exchange_symbol: Exchange-specific symbol
            expected_universal: Expected universal symbol
            exchange: Exchange name for context
            
        Returns:
            True if mapping is correct
        """
        mapping = self.map_symbol(exchange_symbol, exchange)
        return mapping.universal_symbol == expected_universal
    
    def get_all_quote_types(self) -> Dict[QuoteCurrencyType, List[str]]:
        """
        Get all quote currencies grouped by type.
        """
        result = {}
        for quote, quote_type in self.quote_mappings.items():
            if quote_type not in result:
                result[quote_type] = []
            result[quote_type].append(quote)
        return result 