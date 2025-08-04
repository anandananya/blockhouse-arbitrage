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
    metadata: Dict = None  # Additional metadata like stablecoin type, multiplier, etc.

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
        # Common separators
        self.separators = ['-', '_', '/']
        
        # Asset aliases → canonical
        self.asset_aliases = {
            "XBT": "BTC",      # Bitcoin (XBT is sometimes used)
            "WBTC": "BTC",     # Wrapped Bitcoin
            "BCC": "BCH",      # Bitcoin Cash (old symbol)
            "BCHABC": "BCH",   # Bitcoin Cash ABC
            "BCHSV": "BSV",    # Bitcoin Cash SV
            "BONK": "BONK",    # BONK
            "SHIB": "SHIB",    # Shiba Inu
            "DOGE": "DOGE",    # Dogecoin
            "PEPE": "PEPE",    # Pepe
            "WIF": "WIF",      # dogwifhat
        }
        
        # Stablecoins grouped to fiat tags
        self.stablecoin_to_fiat = {
            "USDT": "USD",     # Tether USD
            "USDC": "USD",     # USD Coin
            "BUSD": "USD",     # Binance USD
            "DAI": "USD",      # Dai Stablecoin
            "FDUSD": "USD",    # First Digital USD
            "TUSD": "USD",     # TrueUSD
            "PAX": "USD",      # Paxos Standard
        }
        
        # Known quote currencies (priority order)
        self.known_quotes = list(self.stablecoin_to_fiat.keys()) + [
            "USD", "EUR", "GBP", "JPY", "KRW", "CNY",  # Fiat
            "BTC", "ETH", "BNB", "SOL", "ADA"          # Crypto
        ]
        
        # Contract flags to strip
        self.contract_flags = ["PERP", "SWAP", "FUT", "QUARTERLY", "SPOT"]
        
        # Exchange-specific noise to strip
        self.exchange_noise = ["SPOT:", "FUTURES:", ".P", ":USDT", "^SPOT:", "^FUTURES:"]
        
        # Common quote currency mappings (for backward compatibility)
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
            "MKR": "MKR",
            "CRV": "CRV",
            "SUSHI": "SUSHI",
            "YFI": "YFI",
            "SNX": "SNX",
            "BAL": "BAL",
            "REN": "REN",
            "ZRX": "ZRX",
            "BAT": "BAT",
            "LINK": "LINK",
            "LRC": "LRC",
            "MANA": "MANA",
            "ENJ": "ENJ",
            "SAND": "SAND",
            "AXS": "AXS",
            "CHZ": "CHZ",
            "HOT": "HOT",
            "VET": "VET",
            "VTHO": "VTHO",
            "ICX": "ICX",
            "ONG": "ONG",
            "ONT": "ONT",
            "QTUM": "QTUM",
            "XRP": "XRP",
            "XLM": "XLM",
            "ADA": "ADA",
            "DOT": "DOT",
            "MATIC": "MATIC",
            "AVAX": "AVAX",
            "ATOM": "ATOM",
            "NEAR": "NEAR",
            "FTM": "FTM",
            "ALGO": "ALGO",
            "AR": "AR",
            "FIL": "FIL",
            "ICP": "ICP",
            "APT": "APT",
            "SUI": "SUI",
            "SEI": "SEI",
            "TIA": "TIA",
            "INJ": "INJ",
            "OSMO": "OSMO",
            "JUP": "JUP",
            "PYTH": "PYTH",
            "WLD": "WLD",
            "STRK": "STRK",
            "BLUR": "BLUR",
            "OP": "OP",
            "ARB": "ARB",
            "MAGIC": "MAGIC",
            "IMX": "IMX",
            "STX": "STX",
            "CFX": "CFX",
            "FET": "FET",
            "AGIX": "AGIX",
            "OCEAN": "OCEAN",
            "RNDR": "RNDR",
            "THETA": "THETA",
            "TFUEL": "TFUEL",
            "HBAR": "HBAR",
            "HIVE": "HIVE",
            "HBD": "HBD",
            "STEEM": "STEEM",
            "SBD": "SBD",
            "BTS": "BTS",
            "EOS": "EOS",
            "TRX": "TRX",
            "BTT": "BTT",
            "WIN": "WIN",
            "APENFT": "APENFT",
            "NFT": "NFT",
            "JST": "JST",
            "SUN": "SUN",
            "USDD": "USDD",
            "TUSD": "TUSD",
            "PAX": "PAX",
            "GUSD": "GUSD",
            "FRAX": "FRAX",
            "LUSD": "LUSD",
            "SUSD": "SUSD",
            "MUSD": "MUSD",
            "RSV": "RSV",
            "USDK": "USDK",
            "USDN": "USDN",
            "USDJ": "USDJ",
            "USDP": "USDP",
            "USDT": "USDT",
            "USDC": "USDC",
            "BUSD": "BUSD",
            "DAI": "DAI",
            "FDUSD": "FDUSD",
            "TUSD": "TUSD",
            "PAX": "PAX",
            "GUSD": "GUSD",
            "FRAX": "FRAX",
            "LUSD": "LUSD",
            "SUSD": "SUSD",
            "MUSD": "MUSD",
            "RSV": "RSV",
            "USDK": "USDK",
            "USDN": "USDN",
            "USDJ": "USDJ",
            "USDP": "USDP",
        }
    
    def normalize_symbol(self, symbol: str, exchange: str = "unknown") -> str:
        """
        Normalize a symbol by removing exchange-specific noise and standardizing format.
        
        Args:
            symbol: Raw symbol from exchange
            exchange: Exchange name for context
        
        Returns:
            Normalized symbol string
        """
        # Convert to uppercase and remove spaces
        s = symbol.upper().strip()
        
        # Remove exchange-specific noise
        for noise in self.exchange_noise:
            s = s.replace(noise, "")
        
        # Replace separators with single dash
        for sep in self.separators:
            s = s.replace(sep, "-")
        
        # Remove contract flags
        for flag in self.contract_flags:
            s = s.replace(f"-{flag}", "").replace(flag, "")
        
        # Clean up multiple dashes and strip
        s = re.sub(r'-+', '-', s)
        s = s.strip('-')
        
        return s
    
    def strip_multiplier(self, token: str) -> Tuple[str, int]:
        """
        Strip multiplier prefixes from tokens (e.g., 1000BONK -> BONK, multiplier=1000).
        
        Args:
            token: Token string that might have multiplier prefix
        
        Returns:
            Tuple of (base_token, multiplier)
        """
        match = re.match(r'^(\d+)([A-Z]+)$', token)
        if match:
            multiplier = int(match.group(1))
            base_token = match.group(2)
            return base_token, multiplier
        return token, 1
    
    def split_base_quote(self, symbol: str) -> Tuple[str, str, int]:
        """
        Split symbol into base and quote assets.
        
        Args:
            symbol: Normalized symbol
        
        Returns:
            Tuple of (base, quote, multiplier)
        """
        parts = symbol.split('-')
        
        if len(parts) == 2:
            # Clear separator case: BTC-USDT
            base_part, quote = parts
        else:
            # No separator case: BTCUSDT
            # Try to infer by scanning from end for known quotes
            for quote in sorted(self.known_quotes, key=len, reverse=True):
                if symbol.endswith(quote):
                    base_part = symbol[:-len(quote)]
                    break
            else:
                raise ValueError(f"Cannot infer quote currency from symbol: {symbol}")
        
        # Strip multiplier from base
        base, multiplier = self.strip_multiplier(base_part)
        
        return base, quote, multiplier
    
    def resolve_assets(self, base: str, quote: str) -> Tuple[str, str, Optional[str]]:
        """
        Resolve asset aliases and normalize quote currencies.
        
        Args:
            base: Base asset
            quote: Quote asset
        
        Returns:
            Tuple of (canonical_base, canonical_quote, stablecoin_type)
        """
        # Resolve base asset alias
        canonical_base = self.asset_aliases.get(base, base)
        
        # Resolve quote asset alias
        quote_alias = self.asset_aliases.get(quote, quote)
        
        # Check if quote is a stablecoin that should be normalized to USD
        if quote_alias in self.stablecoin_to_fiat:
            canonical_quote = self.stablecoin_to_fiat[quote_alias]
            stablecoin_type = quote_alias
        else:
            canonical_quote = quote_alias
            stablecoin_type = None
        
        return canonical_base, canonical_quote, stablecoin_type
    
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
        # Normalize the exchange symbol
        normalized_symbol = self.normalize_symbol(exchange_symbol, exchange)
        
        # Split into base and quote
        try:
            base, quote, multiplier = self.split_base_quote(normalized_symbol)
        except ValueError as e:
            # If splitting fails, return a mapping with low confidence
            return SymbolMapping(
                exchange_symbol=exchange_symbol,
                universal_symbol=exchange_symbol, # Cannot map
                base_asset=exchange_symbol,
                quote_asset=exchange_symbol,
                quote_type=QuoteCurrencyType.OTHER,
                confidence=0.1,
                metadata={"error": str(e)}
            )
        
        # Resolve assets and get quote type
        canonical_base, canonical_quote, stablecoin_type = self.resolve_assets(base, quote)
        quote_type = self.get_quote_type(canonical_quote)
        
        # Calculate confidence
        confidence = 0.5  # Base confidence
        
        # Bonus for successful parsing
        if canonical_base and canonical_quote:
            confidence += 0.2
        
        # Bonus for known assets
        if canonical_base in self.asset_mappings:
            confidence += 0.1
        if canonical_quote in self.asset_mappings:
            confidence += 0.1
        
        # Bonus for known quote types
        if quote_type != QuoteCurrencyType.OTHER:
            confidence += 0.1
        
        # Bonus for stablecoin normalization
        if stablecoin_type:
            confidence += 0.1
        
        # Penalty for unknown patterns
        if not canonical_base or not canonical_quote:
            confidence -= 0.3
        
        return SymbolMapping(
            exchange_symbol=exchange_symbol,
            universal_symbol=f"{canonical_base}/{canonical_quote}",
            base_asset=canonical_base,
            quote_asset=canonical_quote,
            quote_type=quote_type,
            confidence=confidence,
            metadata={"stablecoin_type": stablecoin_type}
        )
    
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
            exchange: Target exchange name
        
        Returns:
            Exchange-specific symbol format
        """
        if "/" not in universal_symbol:
            return universal_symbol
        
        base, quote = universal_symbol.split("/", 1)
        
        # Get exchange pattern
        # This part needs to be implemented based on actual exchange patterns
        # For now, we'll use a placeholder
        separator = "-" # Default separator
        quote_suffix = True # Default quote suffix
        
        # Example: If exchange is "binance", it might use "" or "_"
        # If exchange is "okx", it might use "-"
        # This is a simplified example and needs to be refined
        
        # Apply exchange-specific formatting
        if separator == "":
            return f"{base}{quote}"
        elif separator == "_":
            return f"{base}_{quote}"
        else:
            return f"{base}{separator}{quote}"
    
    def validate_mapping(self, exchange_symbol: str, expected_universal: str, 
                        exchange: str = "unknown") -> bool:
        """
        Validate that an exchange symbol maps to the expected universal symbol.
        
        Args:
            exchange_symbol: Exchange-specific symbol
            expected_universal: Expected universal symbol
            exchange: Exchange name
        
        Returns:
            True if mapping matches expected result
        """
        try:
            mapping = self.map_symbol(exchange_symbol, exchange)
            return mapping.universal_symbol == expected_universal
        except Exception:
            return False
    
    def get_all_quote_types(self) -> Dict[QuoteCurrencyType, List[str]]:
        """
        Get all quote currency types and their associated symbols.
        
        Returns:
            Dictionary mapping quote types to lists of symbols
        """
        result = {}
        
        for quote_type in QuoteCurrencyType:
            symbols = []
            for symbol, qt in self.quote_mappings.items():
                if qt == quote_type:
                    symbols.append(symbol)
            result[quote_type] = symbols
        
        return result 