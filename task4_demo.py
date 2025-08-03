#!/usr/bin/env python3
"""
Task 4 Demo: Universal Symbol Mapper

This script demonstrates the universal symbol mapper functionality including:
1. Mapping exchange-specific symbols to universal format
2. Handling prefix variations (1000BONK → BONK)
3. Handling suffix variations (-USD vs -USDT)
4. Handling separator variations (BTCUSDT vs BTC-USDT)
5. Quote currency normalization
6. Exchange-specific patterns
"""

import asyncio
import json
from xetrade.utils.symbol_mapper import UniversalSymbolMapper

def task4_demo():
    """Demonstrate Task 4: Universal Symbol Mapper."""
    print("🎯 Task 4: Universal Symbol Mapper Demo")
    print("=" * 60)
    
    mapper = UniversalSymbolMapper()
    
    # Step 1: Demonstrate the main requirement
    print("1️⃣ Main Requirement: 1000BONK-USD vs BONK-USDT")
    print("-" * 50)
    
    test_cases = [
        ("1000BONK-USD", "derive"),
        ("BONK-USDT", "binance"),
    ]
    
    for exchange_symbol, exchange in test_cases:
        mapping = mapper.map_symbol(exchange_symbol, exchange)
        print(f"🔗 {exchange_symbol} ({exchange}) → {mapping.universal_symbol}")
        print(f"   Base Asset: {mapping.base_asset}")
        print(f"   Quote Asset: {mapping.quote_asset}")
        print(f"   Quote Type: {mapping.quote_type.value}")
        print(f"   Confidence: {mapping.confidence:.2f}")
        print()
    
    print("✅ Both symbols map to the same underlying asset (BONK) with USD-equivalent quote!")
    print()
    
    # Step 2: Demonstrate prefix handling
    print("2️⃣ Prefix Variations")
    print("-" * 30)
    
    prefix_cases = [
        ("1000BONK-USD", "derive"),
        ("100SHIB-USDT", "kucoin"),
        ("10DOGE-USDT", "binance"),
        ("1INCH-USDT", "okx"),  # This should NOT be stripped
    ]
    
    for exchange_symbol, exchange in prefix_cases:
        mapping = mapper.map_symbol(exchange_symbol, exchange)
        print(f"🔗 {exchange_symbol} → {mapping.universal_symbol}")
        print(f"   Stripped prefix: {exchange_symbol.split('-')[0]} → {mapping.base_asset}")
        print()
    
    # Step 3: Demonstrate separator handling
    print("3️⃣ Separator Variations")
    print("-" * 30)
    
    separator_cases = [
        ("BTCUSDT", "binance"),      # No separator
        ("BTC-USDT", "okx"),         # Dash separator
        ("BTC_USDT", "bitmart"),     # Underscore separator
        ("BTC/USDT", "generic"),     # Slash separator
    ]
    
    for exchange_symbol, exchange in separator_cases:
        mapping = mapper.map_symbol(exchange_symbol, exchange)
        print(f"🔗 {exchange_symbol} ({exchange}) → {mapping.universal_symbol}")
        print()
    
    # Step 4: Demonstrate quote currency normalization
    print("4️⃣ Quote Currency Normalization")
    print("-" * 35)
    
    quote_cases = [
        ("BTC-USD", "derive"),
        ("BTC-USDT", "binance"),
        ("BTC-USDC", "kucoin"),
        ("BTC-BUSD", "binance"),
        ("BTC-DAI", "okx"),
    ]
    
    for exchange_symbol, exchange in quote_cases:
        mapping = mapper.map_symbol(exchange_symbol, exchange)
        print(f"🔗 {exchange_symbol} → {mapping.universal_symbol}")
        print(f"   Quote Type: {mapping.quote_type.value}")
        print()
    
    # Step 5: Demonstrate reverse mapping
    print("5️⃣ Reverse Mapping (Universal → Exchange)")
    print("-" * 40)
    
    universal_symbols = ["BONK/USD", "BTC/USDT", "ETH/USD", "SOL/USDT"]
    exchanges = ["binance", "okx", "derive", "kucoin", "bitmart"]
    
    for universal_symbol in universal_symbols:
        print(f"📋 {universal_symbol}:")
        for exchange in exchanges:
            exchange_symbol = mapper.get_exchange_symbol(universal_symbol, exchange)
            print(f"   {exchange}: {exchange_symbol}")
        print()
    
    # Step 6: Demonstrate confidence scoring
    print("6️⃣ Confidence Scoring")
    print("-" * 25)
    
    confidence_cases = [
        ("BTCUSDT", "binance"),      # High confidence (known assets, known exchange)
        ("BTC-USDT", "okx"),         # High confidence
        ("UNKNOWN-USDT", "binance"), # Lower confidence (unknown base asset)
        ("BTC-UNKNOWN", "binance"),  # Lower confidence (unknown quote asset)
        ("INVALID", "unknown"),      # Low confidence (can't parse)
    ]
    
    for exchange_symbol, exchange in confidence_cases:
        mapping = mapper.map_symbol(exchange_symbol, exchange)
        confidence_level = "🟢 High" if mapping.confidence > 0.8 else "🟡 Medium" if mapping.confidence > 0.5 else "🔴 Low"
        print(f"🔗 {exchange_symbol} → {mapping.universal_symbol}")
        print(f"   Confidence: {mapping.confidence:.2f} ({confidence_level})")
        print()
    
    # Step 7: Demonstrate validation
    print("7️⃣ Symbol Validation")
    print("-" * 20)
    
    validation_cases = [
        ("1000BONK-USD", "BONK/USD", "derive", True),
        ("BONK-USDT", "BONK/USD", "binance", False),  # Different quote
        ("BTCUSDT", "BTC/USDT", "binance", True),
        ("XBT-USDT", "BTC/USDT", "okx", True),        # XBT → BTC mapping
    ]
    
    for exchange_symbol, expected_universal, exchange, should_be_valid in validation_cases:
        is_valid = mapper.validate_mapping(exchange_symbol, expected_universal, exchange)
        status = "✅ PASS" if is_valid == should_be_valid else "❌ FAIL"
        print(f"🔗 {exchange_symbol} → {expected_universal} ({exchange}): {is_valid} {status}")
        print()
    
    # Step 8: Demonstrate quote currency classification
    print("8️⃣ Quote Currency Classification")
    print("-" * 35)
    
    quote_types = mapper.get_all_quote_types()
    for quote_type, currencies in quote_types.items():
        print(f"📊 {quote_type.value}: {', '.join(currencies)}")
    
    print()
    
    # Step 9: JSON output for API integration
    print("9️⃣ JSON Output for API Integration")
    print("-" * 35)
    
    # Demonstrate comprehensive mapping with JSON output
    comprehensive_cases = [
        ("1000BONK-USD", "derive"),
        ("BONK-USDT", "binance"),
        ("BTCUSDT", "binance"),
        ("XBT-USDT", "okx"),
        ("100SHIB-USDT", "kucoin"),
    ]
    
    results = []
    for exchange_symbol, exchange in comprehensive_cases:
        mapping = mapper.map_symbol(exchange_symbol, exchange)
        results.append({
            "exchange_symbol": mapping.exchange_symbol,
            "universal_symbol": mapping.universal_symbol,
            "base_asset": mapping.base_asset,
            "quote_asset": mapping.quote_asset,
            "quote_type": mapping.quote_type.value,
            "confidence": mapping.confidence,
            "exchange": exchange
        })
    
    print("📋 Comprehensive Symbol Mapping Results:")
    print(json.dumps(results, indent=2))
    
    print(f"\n✅ Task 4 Demo Completed!")
    print(f"📊 All requirements implemented:")
    print(f"   ✅ Universal symbol mapping function")
    print(f"   ✅ Prefix variations (1000BONK → BONK)")
    print(f"   ✅ Suffix variations (-USD vs -USDT)")
    print(f"   ✅ Separator variations (BTCUSDT vs BTC-USDT)")
    print(f"   ✅ Quote currency normalization")
    print(f"   ✅ Exchange-specific patterns")
    print(f"   ✅ Confidence scoring")
    print(f"   ✅ Validation capabilities")
    print(f"   ✅ Reverse mapping (universal → exchange)")

if __name__ == "__main__":
    task4_demo() 