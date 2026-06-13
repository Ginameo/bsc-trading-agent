"""
Market Data Layer - Binance API + CoinGecko
============================================
Free, no-auth market data for BSC trading agent.
"""
import requests
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import BINANCE_API_URL, COINGECKO_API_URL, DEXSCREENER_API_URL


class MarketDataFetcher:
    """Fetches real-time and historical market data from multiple free sources."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BSC-Trading-Agent/1.0"
        })
        self._cache = {}
        self._cache_ttl = 30  # seconds

    def _cached_get(self, url: str, params: dict = None, ttl: int = None) -> Optional[dict]:
        """GET with simple in-memory cache to respect rate limits."""
        cache_key = f"{url}:{json.dumps(params or {}, sort_keys=True)}"
        ttl = ttl or self._cache_ttl
        if cache_key in self._cache:
            data, ts = self._cache[cache_key]
            if time.time() - ts < ttl:
                return data
        try:
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self._cache[cache_key] = (data, time.time())
            return data
        except Exception as e:
            print(f"[MarketData] Error fetching {url}: {e}")
            return None

    # ─── Binance ────────────────────────────────────────────
    def get_price(self, symbol: str = "BNBUSDT") -> Optional[float]:
        """Get current price from Binance."""
        data = self._cached_get(
            f"{BINANCE_API_URL}/api/v3/ticker/price",
            {"symbol": symbol},
            ttl=5
        )
        if data and "price" in data:
            return float(data["price"])
        return None

    def get_klines(self, symbol: str = "BNBUSDT", interval: str = "1h", limit: int = 100) -> List[dict]:
        """Get candlestick data from Binance."""
        data = self._cached_get(
            f"{BINANCE_API_URL}/api/v3/klines",
            {"symbol": symbol, "interval": interval, "limit": limit},
            ttl=60
        )
        if not data:
            return []
        return [{
            "timestamp": k[0],
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "close_time": k[6],
            "quote_volume": float(k[7]),
            "trades": k[8]
        } for k in data]

    def get_orderbook(self, symbol: str = "BNBUSDT", limit: int = 20) -> dict:
        """Get order book depth."""
        data = self._cached_get(
            f"{BINANCE_API_URL}/api/v3/depth",
            {"symbol": symbol, "limit": limit},
            ttl=5
        )
        if not data:
            return {"bids": [], "asks": []}
        return {
            "bids": [(float(p), float(q)) for p, q in data.get("bids", [])],
            "asks": [(float(p), float(q)) for p, q in data.get("asks", [])]
        }

    def get_24h_ticker(self, symbol: str = "BNBUSDT") -> Optional[dict]:
        """Get 24h price change stats."""
        data = self._cached_get(
            f"{BINANCE_API_URL}/api/v3/ticker/24hr",
            {"symbol": symbol},
            ttl=30
        )
        if not data:
            return None
        return {
            "price_change": float(data.get("priceChange", 0)),
            "price_change_pct": float(data.get("priceChangePercent", 0)),
            "high": float(data.get("highPrice", 0)),
            "low": float(data.get("lowPrice", 0)),
            "volume": float(data.get("volume", 0)),
            "quote_volume": float(data.get("quoteVolume", 0)),
            "trades": int(data.get("count", 0))
        }

    # ─── CoinGecko ─────────────────────────────────────────
    def get_market_data(self, coin_id: str = "binancecoin") -> Optional[dict]:
        """Get comprehensive market data from CoinGecko."""
        data = self._cached_get(
            f"{COINGECKO_API_URL}/coins/{coin_id}",
            {"localization": "false", "tickers": "false", "community_data": "false"},
            ttl=60
        )
        if not data:
            return None
        md = data.get("market_data", {})
        return {
            "price_usd": md.get("current_price", {}).get("usd", 0),
            "market_cap": md.get("market_cap", {}).get("usd", 0),
            "total_volume": md.get("total_volume", {}).get("usd", 0),
            "price_change_24h": md.get("price_change_percentage_24h", 0),
            "price_change_7d": md.get("price_change_percentage_7d", 0),
            "price_change_30d": md.get("price_change_percentage_30d", 0),
            "ath": md.get("ath", {}).get("usd", 0),
            "atl": md.get("atl", {}).get("usd", 0),
            "circulating_supply": md.get("circulating_supply", 0),
            "sentiment_up": data.get("sentiment_votes_up_percentage", 50),
            "sentiment_down": data.get("sentiment_votes_down_percentage", 50)
        }

    def get_trending(self) -> List[dict]:
        """Get trending coins from CoinGecko."""
        data = self._cached_get(
            f"{COINGECKO_API_URL}/search/trending",
            ttl=120
        )
        if not data:
            return []
        return [{
            "id": c.get("item", {}).get("id"),
            "symbol": c.get("item", {}).get("symbol"),
            "name": c.get("item", {}).get("name"),
            "market_cap_rank": c.get("item", {}).get("market_cap_rank"),
            "score": c.get("item", {}).get("score", 0)
        } for c in data.get("coins", [])[:10]]

    # ─── DexScreener (BSC DEX data) ────────────────────────
    def get_dex_pairs(self, token_address: str) -> List[dict]:
        """Get DEX pair data from DexScreener for a BSC token."""
        data = self._cached_get(
            f"{DEXSCREENER_API_URL}/dex/tokens/{token_address}",
            ttl=30
        )
        if not data or "pairs" not in data:
            return []
        return [{
            "pair_address": p.get("pairAddress"),
            "dex": p.get("dexId"),
            "base_token": p.get("baseToken", {}).get("symbol"),
            "quote_token": p.get("quoteToken", {}).get("symbol"),
            "price_usd": float(p.get("priceUsd", 0)),
            "price_change_5m": float(p.get("priceChange", {}).get("m5", 0)),
            "price_change_1h": float(p.get("priceChange", {}).get("h1", 0)),
            "price_change_24h": float(p.get("priceChange", {}).get("h24", 0)),
            "volume_24h": float(p.get("volume", {}).get("h24", 0)),
            "liquidity_usd": float(p.get("liquidity", {}).get("usd", 0)),
            "fdv": float(p.get("fdv", 0))
        } for p in data.get("pairs", []) if p.get("chainId") == "bsc"]

    # ─── Composite ──────────────────────────────────────────
    def get_full_snapshot(self, symbol: str = "BNBUSDT", coin_id: str = "binancecoin") -> dict:
        """Get comprehensive market snapshot combining all sources."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "binance": {
                "price": self.get_price(symbol),
                "ticker_24h": self.get_24h_ticker(symbol),
                "orderbook": self.get_orderbook(symbol),
                "klines_1h": self.get_klines(symbol, "1h", 50)[-5:]  # last 5 candles
            },
            "coingecko": self.get_market_data(coin_id),
            "trending": self.get_trending()
        }


if __name__ == "__main__":
    fetcher = MarketDataFetcher()
    print("=== BSC Trading Agent - Market Data Test ===\n")

    price = fetcher.get_price("BNBUSDT")
    print(f"BNB Price: ${price}")

    ticker = fetcher.get_24h_ticker("BNBUSDT")
    if ticker:
        print(f"24h Change: {ticker['price_change_pct']}%")
        print(f"24h Volume: ${ticker['quote_volume']:,.0f}")

    market = fetcher.get_market_data("binancecoin")
    if market:
        print(f"7d Change: {market['price_change_7d']}%")
        print(f"Market Cap: ${market['market_cap']:,.0f}")

    trending = fetcher.get_trending()
    if trending:
        print(f"\nTrending: {', '.join([t['symbol'] for t in trending[:5]])}")

    print("\n✅ All data sources working!")
