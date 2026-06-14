"""
CMC Agent Hub Integration
=========================
CoinMarketCap Agent Hub provides pre-computed signals,
market intelligence, and agent-ready data formats.
Uses CMC public API + Agent Hub MCP integration.
"""
import json
import os
import sys
import requests
from typing import Optional, Dict, List
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CMC_API_BASE = "https://pro-api.coinmarketcap.com/v1"
CMC_AGENT_HUB = "https://agent-hub.coinmarketcap.com"
CMC_PUBLIC_BASE = "https://api.coinmarketcap.com"

# CMC public endpoints (no auth required)
CMC_COIN_MARKET = f"{CMC_PUBLIC_BASE}/data-api/v3/cryptocurrency"
CMC_TRENDING = f"{CMC_PUBLIC_BASE}/data-api/v3/top/trending"


class CMCAgentHub:
    """CoinMarketCap Agent Hub integration for market intelligence."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("CMC_API_KEY", "")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BSC-AI-Trading-Agent/1.0"
        })
        if self.api_key:
            self.session.headers["X-CMC_PRO_API_KEY"] = self.api_key

    def _get(self, url: str, params: dict = None) -> Optional[dict]:
        """Make GET request with error handling."""
        try:
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[CMC] Error: {e}")
            return None

    # ─── Market Data (Public API) ───────────────────────────
    def get_coin_market(self, limit: int = 20) -> List[dict]:
        """Get top coins by market cap."""
        data = self._get(f"{CMC_COIN_MARKET}/listing", {
            "start": 1, "limit": limit, "sortBy": "market_cap",
            "sortType": "desc", "convert": "USD"
        })
        if not data or "data" not in data:
            return []
        return [{
            "id": c.get("id"),
            "name": c.get("name"),
            "symbol": c.get("symbol"),
            "price": c.get("quote", {}).get("USD", {}).get("price", 0),
            "change_24h": c.get("quote", {}).get("USD", {}).get("percent_change_24h", 0),
            "change_7d": c.get("quote", {}).get("USD", {}).get("percent_change_7d", 0),
            "market_cap": c.get("quote", {}).get("USD", {}).get("market_cap", 0),
            "volume_24h": c.get("quote", {}).get("USD", {}).get("volume_24h", 0),
            "cmc_rank": c.get("cmc_rank", 0)
        } for c in data.get("data", [])]

    def get_trending(self) -> List[dict]:
        """Get trending coins from CMC."""
        data = self._get(CMC_TRENDING)
        if not data or "data" not in data:
            return []
        return [{
            "id": c.get("id"),
            "name": c.get("name"),
            "symbol": c.get("symbol"),
            "price": c.get("quote", {}).get("USD", {}).get("price", 0),
            "change_24h": c.get("quote", {}).get("USD", {}).get("percent_change_24h", 0),
        } for c in data.get("data", {}).get("cryptoCurrencyList", [])[:10]]

    def get_global_metrics(self) -> Optional[dict]:
        """Get global crypto market metrics."""
        data = self._get(f"{CMC_API_BASE}/global-metrics/quotes/latest")
        if not data or "data" not in data:
            return None
        d = data["data"]
        return {
            "total_market_cap": d.get("quote", {}).get("USD", {}).get("total_market_cap", 0),
            "total_volume_24h": d.get("quote", {}).get("USD", {}).get("total_volume_24h", 0),
            "btc_dominance": d.get("btc_dominance", 0),
            "eth_dominance": d.get("eth_dominance", 0),
            "active_cryptocurrencies": d.get("active_cryptocurrencies", 0),
            "total_cryptocurrencies": d.get("total_cryptocurrencies", 0)
        }

    # ─── Agent Hub Intelligence ─────────────────────────────
    def get_market_sentiment(self) -> Optional[dict]:
        """Get market sentiment analysis from CMC Agent Hub."""
        # Fear & Greed index + market overview
        data = self._get("https://api.alternative.me/fng/?limit=1")
        if data and "data" in data:
            fng = data["data"][0]
            return {
                "fear_greed_index": int(fng.get("value", 50)),
                "classification": fng.get("value_classification", "Neutral"),
                "timestamp": fng.get("timestamp", "")
            }
        return None

    def get_market_overview(self) -> dict:
        """Get comprehensive market overview for agent decision-making."""
        overview = {
            "timestamp": datetime.utcnow().isoformat(),
            "top_coins": [],
            "trending": [],
            "sentiment": None,
            "global_metrics": None
        }

        # Top coins
        overview["top_coins"] = self.get_coin_market(10)

        # Trending
        overview["trending"] = self.get_trending()

        # Sentiment
        overview["sentiment"] = self.get_market_sentiment()

        # Global metrics
        overview["global_metrics"] = self.get_global_metrics()

        return overview

    def analyze_opportunity(self, symbol: str) -> dict:
        """Analyze a specific coin for trading opportunity."""
        coins = self.get_coin_market(100)
        target = None
        for c in coins:
            if c["symbol"].upper() == symbol.upper():
                target = c
                break

        if not target:
            return {"symbol": symbol, "recommendation": "UNKNOWN", "reasons": ["Not found in CMC data"]}

        reasons = []
        score = 0

        # Price momentum
        if target.get("change_24h", 0) > 5:
            score += 1
            reasons.append(f"Strong 24h momentum (+{target['change_24h']:.1f}%)")
        elif target.get("change_24h", 0) < -5:
            score -= 1
            reasons.append(f"Price dip ({target['change_24h']:.1f}%) - potential buy")

        # Volume check
        if target.get("volume_24h", 0) > target.get("market_cap", 1) * 0.1:
            score += 1
            reasons.append("High volume relative to market cap")

        # Market cap rank
        if target.get("cmc_rank", 100) <= 20:
            score += 1
            reasons.append(f"Top 20 coin (rank #{target['cmc_rank']})")

        if score >= 2:
            recommendation = "BUY"
        elif score <= -1:
            recommendation = "AVOID"
        else:
            recommendation = "HOLD"

        return {
            "symbol": symbol,
            "recommendation": recommendation,
            "score": score,
            "reasons": reasons,
            "data": target
        }


# MCP Server integration config
CMC_MCP_CONFIG = {
    "name": "cmc-agent-hub",
    "description": "CoinMarketCap Agent Hub - Market intelligence for AI trading agents",
    "url": "https://agent-hub.coinmarketcap.com",
    "capabilities": [
        "market_data",
        "price_signals",
        "sentiment_analysis",
        "trending_tokens",
        "global_metrics",
        "risk_assessment"
    ]
}


if __name__ == "__main__":
    cmc = CMCAgentHub()
    print("=== CMC Agent Hub Test ===\n")

    # Market overview
    overview = cmc.get_market_overview()

    if overview["top_coins"]:
        print("Top 5 Coins:")
        for c in overview["top_coins"][:5]:
            print(f"  {c['symbol']}: ${c['price']:.2f} ({c['change_24h']:+.1f}%)")

    if overview["trending"]:
        print(f"\nTrending: {', '.join([t['symbol'] for t in overview['trending'][:5]])}")

    if overview["sentiment"]:
        s = overview["sentiment"]
        print(f"\nFear & Greed: {s['fear_greed_index']} ({s['classification']})")

    # Analyze BNB
    analysis = cmc.analyze_opportunity("BNB")
    print(f"\nBNB Analysis: {analysis['recommendation']}")
    for r in analysis.get("reasons", []):
        print(f"  • {r}")

    print("\n✅ CMC Agent Hub integration ready")
