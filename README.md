# 🤖 BSC AI Trading Agent

**Autonomous trading agent on BNB Chain** — built for [BNB Hack: AI Trading Agent Edition](https://dorahacks.io/hackathon/bnbhack-twt-cmc/detail)

## What It Does

An AI-powered trading agent that:
- Fetches real-time market data from **Binance API** + **CoinGecko** (free, no auth)
- Runs multi-signal technical analysis (RSI, MACD, Bollinger Bands, Volume, Order Book)
- Executes trades on-chain via **PancakeSwap** on BSC
- Includes a backtesting engine to validate strategies before going live
- Web dashboard for real-time monitoring

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Dashboard (Flask)               │
│            Real-time monitoring UI               │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│              Trading Agent Core                  │
│  ┌───────────┐  ┌───────────┐  ┌──────────────┐│
│  │ Market    │  │ Strategy  │  │  Execution   ││
│  │ Data      │──│ Engine    │──│  Layer       ││
│  │ Layer     │  │ (Multi-   │  │  (BSC on-    ││
│  │ (Binance  │  │  Signal)  │  │   chain)     ││
│  │ +CoinGecko│  │           │  │              ││
│  │ +DexScre) │  │           │  │              ││
│  └───────────┘  └───────────┘  └──────────────┘│
└─────────────────────────────────────────────────┘
```

## Signals & Strategy

The strategy engine combines multiple independent signals:

| Signal | Weight | Description |
|--------|--------|-------------|
| RSI | 0.8 | Momentum (oversold <30, overbought >70) |
| MACD | 0.7 | Trend (bullish/bearish crossover) |
| Bollinger Bands | 0.6 | Volatility (price relative to bands) |
| Volume | 1.3x amp | High volume amplifies existing signals |
| Order Book | 0.4 | Buy/sell pressure imbalance |
| Sentiment | 0.3 | CoinGecko community sentiment |

Signals are combined into a composite score with confidence 0-1. Trades only execute when confidence ≥ 0.7.

## Quick Start

```bash
# Clone & setup
git clone https://github.com/Ginameo/bsc-trading-agent.git
cd bsc-trading-agent
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your wallet private key

# Run paper trading
PYTHONPATH=. python3 src/agent.py

# Run live trading
PYTHONPATH=. python3 src/agent.py --live

# Run backtest
PYTHONPATH=. python3 src/strategies/backtester.py

# Run dashboard
PYTHONPATH=. python3 src/dashboard.py
```

## Components

### Market Data (`src/data/market_data.py`)
- **Binance API**: Real-time prices, candlesticks, order books, 24h stats
- **CoinGecko API**: Market cap, sentiment, trending coins
- **DexScreener API**: BSC DEX pair data, liquidity, price changes
- All endpoints are **free, no authentication required**

### Strategy Engine (`src/strategies/engine.py`)
- Multi-signal technical analysis
- Configurable weights and thresholds
- Risk management (stop-loss, take-profit, position sizing)

### Backtester (`src/strategies/backtester.py`)
- Historical simulation on Binance candle data
- Tracks win rate, PnL, Sharpe ratio, max drawdown
- Example result: **+5.12% PnL, 100% win rate, 1.68 Sharpe** (1h BNB, 200 candles)

### Executor (`src/execution/executor.py`)
- BSC on-chain execution via PancakeSwap Router V2
- Supports buy (BNB→Token) and sell (Token→BNB)
- Auto-approval for ERC20 tokens
- Slippage protection

### Dashboard (`src/dashboard.py`)
- Real-time web UI with Flask
- Price, signals, wallet balance, trending coins
- Auto-refresh every 30 seconds

## Risk Management

- **Max trade size**: 0.01 BNB (configurable)
- **Stop loss**: 3% (configurable)
- **Take profit**: 5% (configurable)
- **Max open positions**: 3
- **Paper trading mode**: Default ON — test before going live

## Tech Stack

- **Python 3.12** — core language
- **web3.py** — BSC blockchain interaction
- **Flask** — dashboard
- **pandas/numpy** — data analysis
- **Binance API** — market data
- **CoinGecko API** — market data
- **PancakeSwap V2** — DEX execution

## License

MIT

---

Built with 🐱 for BNB Hack: AI Trading Agent Edition
