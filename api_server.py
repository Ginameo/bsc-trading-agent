"""
VPS Backend API Server
======================
Serves trading agent status and data for the dashboard.
Runs on port 5000 alongside the trading agent.
"""
import json
import os
import sys
import time
import threading
from datetime import datetime
from flask import Flask, jsonify, Response
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.data.market_data import MarketDataFetcher
from src.strategies.engine import TradingStrategy, Signal

app = Flask(__name__)
CORS(app)

fetcher = MarketDataFetcher()
strategy = TradingStrategy()

# Shared state
agent_status = {
    "running": False,
    "mode": "PAPER",
    "started_at": None,
    "total_signals": 0,
    "total_trades": 0,
    "winning_trades": 0,
    "losing_trades": 0,
    "last_signal": None,
    "last_trade": None,
    "trade_history": []
}


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


@app.route("/api/status")
def status():
    """Full status for dashboard."""
    price = fetcher.get_price("BNBUSDT")
    ticker = fetcher.get_24h_ticker("BNBUSDT")
    klines = fetcher.get_klines("BNBUSDT", "1h", 100)
    orderbook = fetcher.get_orderbook("BNBUSDT")
    sentiment = fetcher.get_market_data("binancecoin") or {}
    trending = fetcher.get_trending()

    signal = None
    if klines:
        sig = strategy.analyze(klines, orderbook, sentiment)
        signal = {
            "signal": sig.signal.value,
            "confidence": sig.confidence,
            "reasons": sig.reasons,
            "price": sig.price,
            "timestamp": sig.timestamp
        }

    return jsonify({
        "binance": {
            "price": price,
            "ticker_24h": ticker
        },
        "coingecko": sentiment,
        "trending": trending,
        "signal": signal,
        "agent": agent_status,
        "wallet": "0x6D89b06649830B86a72b4385f9703d3B4bdb174b",
        "mode": agent_status["mode"]
    })


@app.route("/api/klines/<interval>/<int:limit>")
def klines(interval, limit):
    """Get candlestick data."""
    data = fetcher.get_klines("BNBUSDT", interval, min(limit, 500))
    return jsonify({"klines": data})


@app.route("/api/agent/status")
def agent():
    """Agent-specific status."""
    return jsonify(agent_status)


@app.route("/api/trades")
def trades():
    """Trade history."""
    return jsonify({"trades": agent_status["trade_history"][-50:]})


def update_agent_status(signal_data, trade_data=None):
    """Update shared agent state."""
    agent_status["last_signal"] = signal_data
    agent_status["total_signals"] += 1
    if trade_data:
        agent_status["last_trade"] = trade_data
        agent_status["total_trades"] += 1
        agent_status["trade_history"].append(trade_data)


if __name__ == "__main__":
    print("[VPS API] Starting on port 5000...")
    app.run(host="0.0.0.0", port=5000, debug=False)
