# Cross-Exchange Trading Engine Core

A high-performance Python application that interacts with multiple cryptocurrency exchanges to provide unified market data, order book analysis, and funding rate calculations.

## 🚀 Features

### ✅ Implemented Exchanges
- **OKX** - Full support (spot + perpetual futures)
- **KuCoin** - Full support (spot + perpetual futures)  
- **Bitmart** - Spot trading support
- **Derive (dYdX)** - Decentralized exchange support
- **Binance** - Full support (geographic restrictions may apply)

### 📊 Core Functionality

#### 1. Best Bid & Ask Across Venues
```bash
# Get best bid/ask across multiple exchanges
python cli.py best --pair BTC-USDT --venues okx,kucoin,bitmart,derive
```

#### 2. L2 Order Book Depth
```bash
# Get full order book from a specific exchange
python cli.py l2 --venue okx --pair BTC-USDT --depth 100
```

#### 3. Price Impact Analysis
```bash
# Calculate price impact for a large trade
python cli.py impact --venue okx --pair BTC-USDT --side buy --quote 50000
```

#### 4. Funding Rate Analysis
```bash
# Get current and predicted funding rates
python cli.py funding --venue okx --pair BTC-USDT
```

## 🛠 Installation

```bash
# Install in development mode
pip install -e .

# Run the demo
python demo.py
```

## 📋 API Reference

### CLI Commands

#### `best` - Best Bid/Ask Across Venues
```bash
python cli.py best --pair BTC-USDT --venues okx,kucoin,bitmart
```
Returns the best bid and ask prices across all specified venues.

#### `l2` - Level 2 Order Book
```bash
python cli.py l2 --venue okx --pair BTC-USDT --depth 100
```
Returns the full-depth order book with all price levels and quantities.

#### `impact` - Price Impact Analysis
```bash
python cli.py impact --venue okx --pair BTC-USDT --side buy --quote 50000
```
Calculates the effective execution price and price impact for a given trade size.

#### `funding` - Funding Rate Analysis
```bash
python cli.py funding --venue okx --pair BTC-USDT
```
Returns current and predicted funding rates with APR calculations.

### Programmatic Usage

```python
import asyncio
from xetrade.exchanges.base import make_exchanges
from xetrade.models import Pair
from xetrade.services.aggregator import best_across_venues

async def example():
    # Initialize exchanges
    exchanges = make_exchanges(["okx", "kucoin"])
    pair = Pair.parse("BTC-USDT")
    
    # Get best bid/ask across venues
    result = await best_across_venues(exchanges, pair)
    print(f"Best bid: {result['best_bid']}")
    print(f"Best ask: {result['best_ask']}")
    print(f"Mid price: {result['mid']}")

asyncio.run(example())
```

## 🏗 Architecture

### Modular Exchange Design
- **Base Exchange Class**: Common interface for all exchanges
- **Exchange Registry**: Automatic registration of new exchanges
- **Standardized APIs**: Unified data structures across all venues

### Core Services

#### Aggregator Service
- Cross-venue best bid/ask aggregation
- Error handling and fallback mechanisms
- Real-time price comparison

#### Price Impact Service
- Order book walking algorithms
- Price impact calculations
- Trade size optimization

#### Funding Service
- APR/APY calculations from periodic rates
- Historical funding rate analysis
- Multi-interval support (1h, 4h, 8h)

### Data Models
- **Pair**: Trading pair representation (BTC-USDT)
- **Quote**: Best bid/ask with timestamp
- **OrderBook**: Full L2 order book with levels
- **FundingSnapshot**: Current and predicted funding rates

## 🔧 Exchange-Specific Notes

### OKX
- **Symbol Format**: `BTC-USDT` (spot), `BTC-USDT-SWAP` (futures)
- **Funding Interval**: 8 hours
- **API Base**: `https://www.okx.com`

### KuCoin
- **Symbol Format**: `BTC-USDT`
- **Funding Interval**: 8 hours
- **API Base**: `https://api.kucoin.com`

### Bitmart
- **Symbol Format**: `BTC_USDT`
- **Funding**: Spot only (no perpetual futures)
- **API Base**: `https://api-cloud.bitmart.com`

### Derive (dYdX)
- **Symbol Format**: `BTC-USD` (converts USDT to USD)
- **Funding Interval**: 1 hour
- **API Base**: `https://api.dydx.exchange`

### Binance
- **Symbol Format**: `BTCUSDT`
- **Funding Interval**: 8 hours
- **API Base**: `https://api.binance.com`
- **Note**: May have geographic restrictions

## 📊 Price Impact Formula

Price impact is calculated as:
```
Price Impact = (AverageExecutionPrice - MarketMidPrice) / MarketMidPrice × 100%
```

## 🧮 APR Calculation

The system includes utilities to convert periodic funding rates to APR/APY:

```python
from xetrade.services.funding import apr_from_periodic, apy_from_periodic

# Example: 0.01% funding rate every 8 hours
rate = 0.0001
interval_hours = 8.0

apr = apr_from_periodic(rate, interval_hours)  # 0.1095%
apy = apy_from_periodic(rate, interval_hours)  # 0.1157%
```

## 🚨 Error Handling

The system gracefully handles:
- Network timeouts and retries
- Exchange API errors
- Geographic restrictions
- Missing or invalid data
- Rate limiting

## 🔄 Adding New Exchanges

To add a new exchange:

1. Create a new file in `src/xetrade/exchanges/`
2. Inherit from `BaseExchange`
3. Implement required methods
4. Use the `@register_exchange` decorator
5. Add import to `src/xetrade/exchanges/__init__.py`

Example:
```python
@register_exchange
class NewExchange(BaseExchange):
    name = "newexchange"
    
    async def get_best_bid_ask(self, pair: Pair) -> Quote:
        # Implementation here
        pass
```

## 📈 Performance Features

- **Async/Await**: Non-blocking HTTP requests
- **Connection Pooling**: Reusable HTTP sessions
- **Error Recovery**: Automatic retries with exponential backoff
- **Rate Limiting**: Respects exchange rate limits
- **Memory Efficient**: Streaming data processing

## 🧪 Testing

Run the comprehensive demo:
```bash
python demo.py
```

Test individual functionality:
```bash
# Test best bid/ask
python cli.py best --pair BTC-USDT --venues okx,kucoin

# Test order book
python cli.py l2 --venue okx --pair BTC-USDT --depth 10

# Test price impact
python cli.py impact --venue okx --pair BTC-USDT --side buy --quote 10000

# Test funding rates
python cli.py funding --venue okx --pair BTC-USDT
```

## 📝 License

This project is part of a work trial for cross-exchange trading engine development.