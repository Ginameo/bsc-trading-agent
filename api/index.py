"""
Vercel Serverless Function - BSC Trading Agent API
===================================================
"""
import json
import sys
import os
from http.server import BaseHTTPRequestHandler

# Inline market data fetcher (no external deps for serverless)
import urllib.request
import urllib.error

BINANCE_API = "https://api.binance.com"
COINGECKO_API = "https://api.coingecko.com/api/v3"

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BSC-Agent/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return None

def get_bnb_price():
    # Try Binance first, fallback to CoinGecko
    data = fetch_json(f"{BINANCE_API}/api/v3/ticker/price?symbol=BNBUSDT")
    if data and "price" in data:
        return float(data["price"])
    # CoinGecko fallback
    cg = fetch_json(f"{COINGECKO_API}/simple/price?ids=binancecoin&vs_currencies=usd")
    if cg and "binancecoin" in cg:
        return float(cg["binancecoin"]["usd"])
    return None

def get_24h_ticker():
    # Try Binance first
    data = fetch_json(f"{BINANCE_API}/api/v3/ticker/24hr?symbol=BNBUSDT")
    if data and "priceChangePercent" in data:
        return {
            "price_change_pct": float(data.get("priceChangePercent", 0)),
            "high": float(data.get("highPrice", 0)),
            "low": float(data.get("lowPrice", 0)),
            "volume": float(data.get("quoteVolume", 0)),
            "trades": int(data.get("count", 0))
        }
    # CoinGecko fallback
    cg = fetch_json(f"{COINGECKO_API}/coins/binancecoin?localization=false&tickers=false&community_data=false")
    if cg:
        md = cg.get("market_data", {})
        return {
            "price_change_pct": float(md.get("price_change_percentage_24h", 0)),
            "high": float(md.get("high_24h", {}).get("usd", 0)),
            "low": float(md.get("low_24h", {}).get("usd", 0)),
            "volume": float(md.get("total_volume", {}).get("usd", 0)),
            "trades": 0
        }
    return None

def get_klines(interval="1h", limit=100):
    # Try Binance first
    data = fetch_json(f"{BINANCE_API}/api/v3/klines?symbol=BNBUSDT&interval={interval}&limit={limit}")
    if data and len(data) > 10:
        return [{
            "open": float(k[1]), "high": float(k[2]),
            "low": float(k[3]), "close": float(k[4]),
            "volume": float(k[5])
        } for k in data]
    # CoinGecko fallback (market_chart)
    cg = fetch_json(f"{COINGECKO_API}/coins/binancecoin/market_chart?vs_currency=usd&days=7")
    if cg and "prices" in cg:
        prices = cg["prices"]
        volumes = cg.get("total_volumes", [])
        result = []
        for i in range(1, len(prices)):
            p = prices[i][1]
            p_prev = prices[i-1][1]
            vol = volumes[i][1] if i < len(volumes) else 0
            result.append({
                "open": p_prev, "high": max(p, p_prev),
                "low": min(p, p_prev), "close": p,
                "volume": vol
            })
        return result[-limit:]
    return []

def get_coingecko():
    data = fetch_json(f"{COINGECKO_API}/coins/binancecoin?localization=false&tickers=false&community_data=false")
    if not data:
        return None
    md = data.get("market_data", {})
    return {
        "price_usd": md.get("current_price", {}).get("usd", 0),
        "market_cap": md.get("market_cap", {}).get("usd", 0),
        "price_change_24h": md.get("price_change_percentage_24h", 0),
        "price_change_7d": md.get("price_change_percentage_7d", 0),
        "sentiment_up": data.get("sentiment_votes_up_percentage", 50),
        "sentiment_down": data.get("sentiment_votes_down_percentage", 50)
    }

def get_trending():
    data = fetch_json(f"{COINGECKO_API}/search/trending")
    if not data:
        return []
    return [{
        "symbol": c.get("item", {}).get("symbol", ""),
        "name": c.get("item", {}).get("name", ""),
        "score": c.get("item", {}).get("score", 0)
    } for c in data.get("coins", [])[:8]]

def simple_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    deltas = [prices[i] - prices[i-1] for i in range(len(prices)-period, len(prices))]
    gains = [d for d in deltas if d > 0]
    losses = [-d for d in deltas if d < 0]
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0.001
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)

def analyze_signal(klines):
    if len(klines) < 26:
        return {"signal": "HOLD", "confidence": 0, "reasons": ["Insufficient data"]}
    
    closes = [k["close"] for k in klines]
    reasons = []
    scores = []
    
    # RSI
    rsi = simple_rsi(closes)
    if rsi is not None:
        if rsi < 30:
            scores.append(0.8); reasons.append(f"RSI oversold ({rsi})")
        elif rsi < 40:
            scores.append(0.5); reasons.append(f"RSI low ({rsi})")
        elif rsi > 70:
            scores.append(-0.8); reasons.append(f"RSI overbought ({rsi})")
        elif rsi > 60:
            scores.append(-0.4); reasons.append(f"RSI high ({rsi})")
        else:
            reasons.append(f"RSI neutral ({rsi})")
    
    # Simple trend (SMA crossover)
    if len(closes) >= 50:
        sma20 = sum(closes[-20:]) / 20
        sma50 = sum(closes[-50:]) / 50
        if sma20 > sma50:
            scores.append(0.6); reasons.append("SMA20 > SMA50 (bullish)")
        else:
            scores.append(-0.6); reasons.append("SMA20 < SMA50 (bearish)")
    
    # Volume trend
    volumes = [k["volume"] for k in klines[-20:]]
    avg_vol = sum(volumes) / len(volumes) if volumes else 1
    current_vol = klines[-1]["volume"]
    vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1
    if vol_ratio > 1.5:
        reasons.append(f"High volume ({vol_ratio:.1f}x avg)")
    
    avg = sum(scores) / len(scores) if scores else 0
    confidence = min(abs(avg), 1.0)
    
    if avg > 0.5: signal = "STRONG_BUY"
    elif avg > 0.2: signal = "BUY"
    elif avg < -0.5: signal = "STRONG_SELL"
    elif avg < -0.2: signal = "SELL"
    else: signal = "HOLD"
    
    return {"signal": signal, "confidence": round(confidence, 2), "reasons": reasons}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        if self.path == "/api/health":
            self.wfile.write(json.dumps({"status": "ok"}).encode())
            return
        
        # Full status endpoint
        price = get_bnb_price()
        ticker = get_24h_ticker()
        klines = get_klines("1h", 100)
        cg = get_coingecko()
        trending = get_trending()
        signal = analyze_signal(klines) if klines else None
        
        result = {
            "binance": {
                "price": price,
                "ticker_24h": ticker
            },
            "coingecko": cg,
            "trending": trending,
            "signal": signal,
            "wallet": "0x6D89b06649830B86a72b4385f9703d3B4bdb174b",
            "mode": "PAPER"
        }
        
        self.wfile.write(json.dumps(result).encode())
    
    def log_message(self, format, *args):
        pass  # Suppress logs in serverless
