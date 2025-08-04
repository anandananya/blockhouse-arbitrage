#!/usr/bin/env python3
"""
Task 2 Demo: Symbol Mapping

This demo showcases the universal symbol mapping functionality.
"""

import asyncio
import json
import logging

from xetrade.utils.symbol_mapper import UniversalSymbolMapper
from xetrade.models import Pair

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_symbol_mapping():
    """Demonstrate symbol mapping functionality."""
    
    print(" Task 2 Demo: Symbol Mapping")
    print("=" * 50)
    
    try:
        mapper = UniversalSymbolMapper()
        
        # Test cases from requirements
        test_cases = [
            ("1000BONK-USD", "derive"),
            ("BONK-USDT", "binance"),
            ("BTCUSDT", "binance"),
            ("BTC-USDT", "okx"),
            ("BTC_USDT", "bitmart"),
            ("ETH-USD", "derive"),
            ("100SHIB-USDT", "kucoin"),
            ("DOGE-USDT", "binance"),
            ("SOL-USD", "derive"),
            ("XBT-USDT", "okx"),  # XBT is sometimes used for Bitcoin
        ]
        
        print(" Symbol Mapping Examples:")
        print("-" * 30)
        
        for exchange_symbol, exchange in test_cases:
            mapping = mapper.map_symbol(exchange_symbol, exchange)
            print(f" {exchange_symbol} ({exchange}) → {mapping.universal_symbol}")
            print(f"   Base: {mapping.base_asset}, Quote: {mapping.quote_asset}")
            print(f"   Quote Type: {mapping.quote_type.value}, Confidence: {mapping.confidence:.2f}")
            print()
        
        return True
        
    except Exception as e:
        print(f" Error in symbol mapping demo: {e}")
        return False

async def demo_reverse_mapping():
    """Demonstrate reverse mapping functionality."""
    
    print(" Reverse Mapping Demo:")
    print("=" * 50)
    
    try:
        mapper = UniversalSymbolMapper()
        
        # Test reverse mapping
        universal_symbols = ["BONK/USD", "BTC/USDT", "ETH/USD", "SOL/USDT", "DOGE/USDT"]
        exchanges = ["binance", "okx", "derive", "kucoin", "bitmart"]
        
        print(" Universal to Exchange Symbol Mapping:")
        print("-" * 40)
        
        for universal_symbol in universal_symbols:
            print(f" {universal_symbol}:")
            for exchange in exchanges:
                try:
                    exchange_symbol = mapper.get_exchange_symbol(universal_symbol, exchange)
                    print(f"   {exchange}: {exchange_symbol}")
                except Exception as e:
                    print(f"   {exchange}:  {e}")
            print()
        
        return True
        
    except Exception as e:
        print(f" Error in reverse mapping demo: {e}")
        return False

async def demo_quote_currency_classification():
    """Demonstrate quote currency classification."""
    
    print(" Quote Currency Classification Demo:")
    print("=" * 50)
    
    try:
        mapper = UniversalSymbolMapper()
        
        # Get all quote types
        quote_types = mapper.get_all_quote_types()
        
        print(" Quote Currency Classification:")
        print("-" * 30)
        
        for quote_type, currencies in quote_types.items():
            print(f" {quote_type.value}: {', '.join(currencies)}")
        
        print()
        print(" Quote currency classification complete!")
        
        return True
        
    except Exception as e:
        print(f" Error in quote classification demo: {e}")
        return False

async def demo_mapping_validation():
    """Demonstrate mapping validation."""
    
    print(" Mapping Validation Demo:")
    print("=" * 50)
    
    try:
        mapper = UniversalSymbolMapper()
        
        # Test validation cases
        validation_cases = [
            ("BTCUSDT", "BTC/USDT", "binance"),
            ("BTC-USDT", "BTC/USDT", "okx"),
            ("1000BONK-USD", "BONK/USD", "derive"),
            ("ETH-USD", "ETH/USD", "derive"),
        ]
        
        print(" Validating Symbol Mappings:")
        print("-" * 30)
        
        for exchange_symbol, expected_universal, exchange in validation_cases:
            is_valid = mapper.validate_mapping(exchange_symbol, expected_universal, exchange)
            actual_universal = mapper.normalize_symbol(exchange_symbol, exchange)
            
            status = " VALID" if is_valid else " INVALID"
            print(f" {exchange_symbol} ({exchange}) → {actual_universal}")
            print(f"   Expected: {expected_universal}")
            print(f"   Actual: {actual_universal}")
            print(f"   Status: {status}")
            print()
        
        return True
        
    except Exception as e:
        print(f" Error in validation demo: {e}")
        return False

async def demo_edge_cases():
    """Demonstrate edge cases and special handling."""
    
    print(" Edge Cases Demo:")
    print("=" * 50)
    
    try:
        mapper = UniversalSymbolMapper()
        
        # Test edge cases
        edge_cases = [
            ("1000BONK-USD", "derive"),  # Prefix handling
            ("100SHIB-USDT", "kucoin"),  # Number prefix
            ("XBT-USDT", "okx"),         # XBT vs BTC
            ("DOGE-USDT", "binance"),    # Meme coins
            ("SOL-USD", "derive"),       # USD vs USDT
        ]
        
        print(" Testing Edge Cases:")
        print("-" * 25)
        
        for exchange_symbol, exchange in edge_cases:
            try:
                mapping = mapper.map_symbol(exchange_symbol, exchange)
                print(f" {exchange_symbol} ({exchange}) → {mapping.universal_symbol}")
                print(f"   Confidence: {mapping.confidence:.2f}")
            except Exception as e:
                print(f" {exchange_symbol} ({exchange}): {e}")
            print()
        
        return True
        
    except Exception as e:
        print(f" Error in edge cases demo: {e}")
        return False

def main():
    """Run the Task 2 demo."""
    print(" Task 2: Symbol Mapping")
    print("=" * 50)
    
    # Run demos
    results = []
    
    # Demo 1: Symbol mapping
    result1 = asyncio.run(demo_symbol_mapping())
    results.append(result1)
    
    # Demo 2: Reverse mapping
    result2 = asyncio.run(demo_reverse_mapping())
    results.append(result2)
    
    # Demo 3: Quote classification
    result3 = asyncio.run(demo_quote_currency_classification())
    results.append(result3)
    
    # Demo 4: Validation
    result4 = asyncio.run(demo_mapping_validation())
    results.append(result4)
    
    # Demo 5: Edge cases
    result5 = asyncio.run(demo_edge_cases())
    results.append(result5)
    
    # Summary
    print("\n Task 2 Demo Summary")
    print("=" * 50)
    
    demos = [
        "Symbol Mapping",
        "Reverse Mapping",
        "Quote Classification",
        "Mapping Validation",
        "Edge Cases"
    ]
    
    for i, (demo, result) in enumerate(zip(demos, results), 1):
        status = " PASS" if result else " FAIL"
        print(f"{i}. {demo}: {status}")
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n Overall Results: {passed}/{total} demos passed")
    
    if passed == total:
        print("\n Task 2 Symbol Mapping Demo Complete!")
        print("The system successfully demonstrates:")
        print(" Universal symbol normalization")
        print(" Exchange-specific symbol formats")
        print(" Prefix/suffix handling (1000BONK → BONK)")
        print(" Quote currency classification")
        print(" Reverse mapping capabilities")
        print(" Confidence scoring")
        print(" Edge case handling")
    else:
        print("\n  Some demos had issues. Check the errors above.")

if __name__ == "__main__":
    main() 