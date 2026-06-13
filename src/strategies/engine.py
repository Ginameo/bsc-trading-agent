"""
Trading Strategy Engine
=======================
Multi-signal AI-powered strategy combining technical analysis,
market sentiment, and on-chain metrics.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Signal(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class TradeSignal:
    signal: Signal
    confidence: float  # 0.0 - 1.0
    reasons: List[str]
    timestamp: str = ""
    symbol: str = ""
    price: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class Position:
    symbol: str
    entry_price: float
    amount: float
    side: str  # "long" or "short"
    stop_loss: float
    take_profit: float
    opened_at: str = ""
    pnl: float = 0.0

    def update_pnl(self, current_price: float):
        if self.side == "long":
            self.pnl = (current_price - self.entry_price) / self.entry_price * 100
        else:
            self.pnl = (self.entry_price - current_price) / self.entry_price * 100


class TechnicalAnalysis:
    """Pure TA indicators computed from candle data."""

    @staticmethod
    def sma(prices: List[float], period: int) -> List[float]:
        if len(prices) < period:
            return []
        return [np.mean(prices[i:i+period]) for i in range(len(prices) - period + 1)]

    @staticmethod
    def ema(prices: List[float], period: int) -> List[float]:
        if len(prices) < period:
            return []
        multiplier = 2 / (period + 1)
        ema_vals = [np.mean(prices[:period])]
        for price in prices[period:]:
            ema_vals.append((price - ema_vals[-1]) * multiplier + ema_vals[-1])
        return ema_vals

    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> Optional[float]:
        if len(prices) < period + 1:
            return None
        deltas = np.diff(prices[-(period+1):])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(prices: List[float]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        if len(prices) < 26:
            return None, None, None
        ema12 = TechnicalAnalysis.ema(prices, 12)
        ema26 = TechnicalAnalysis.ema(prices, 26)
        if not ema12 or not ema26:
            return None, None, None
        # Align lengths
        min_len = min(len(ema12), len(ema26))
        macd_line = [ema12[-min_len+i] - ema26[-min_len+i] for i in range(min_len)]
        if len(macd_line) < 9:
            return macd_line[-1] if macd_line else None, None, None
        signal_line = TechnicalAnalysis.ema(macd_line, 9)
        if not signal_line:
            return macd_line[-1], None, None
        histogram = macd_line[-1] - signal_line[-1]
        return macd_line[-1], signal_line[-1], histogram

    @staticmethod
    def bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Optional[dict]:
        if len(prices) < period:
            return None
        recent = prices[-period:]
        middle = np.mean(recent)
        std = np.std(recent)
        return {
            "upper": middle + std_dev * std,
            "middle": middle,
            "lower": middle - std_dev * std,
            "current_price": prices[-1],
            "bandwidth": (std_dev * std * 2) / middle * 100
        }

    @staticmethod
    def volume_analysis(volumes: List[float], period: int = 20) -> Optional[dict]:
        if len(volumes) < period:
            return None
        avg_vol = np.mean(volumes[-period:])
        current_vol = volumes[-1]
        return {
            "current": current_vol,
            "average": avg_vol,
            "ratio": current_vol / avg_vol if avg_vol > 0 else 1.0,
            "is_high_volume": current_vol > avg_vol * 1.5
        }


class TradingStrategy:
    """
    Multi-signal strategy combining:
    - RSI (momentum)
    - MACD (trend)
    - Bollinger Bands (volatility)
    - Volume analysis
    - Market sentiment (CoinGecko)
    - Order book imbalance
    """

    def __init__(self):
        self.ta = TechnicalAnalysis()
        self.open_positions: List[Position] = []
        self.trade_history: List[dict] = []

    def analyze(self, klines: List[dict], orderbook: dict = None,
                sentiment: dict = None) -> TradeSignal:
        """Run full analysis and generate trade signal."""
        if len(klines) < 26:
            return TradeSignal(Signal.HOLD, 0.0, ["Insufficient data"])

        closes = [k["close"] for k in klines]
        volumes = [k["volume"] for k in klines]
        current_price = closes[-1]
        reasons = []
        scores = []

        # ── RSI Signal ──
        rsi = self.ta.rsi(closes)
        if rsi is not None:
            if rsi < 30:
                scores.append(0.8)
                reasons.append(f"RSI oversold ({rsi:.1f})")
            elif rsi < 40:
                scores.append(0.6)
                reasons.append(f"RSI approaching oversold ({rsi:.1f})")
            elif rsi > 70:
                scores.append(-0.8)
                reasons.append(f"RSI overbought ({rsi:.1f})")
            elif rsi > 60:
                scores.append(-0.4)
                reasons.append(f"RSI approaching overbought ({rsi:.1f})")
            else:
                scores.append(0.0)
                reasons.append(f"RSI neutral ({rsi:.1f})")

        # ── MACD Signal ──
        macd_val, signal_val, histogram = self.ta.macd(closes)
        if macd_val is not None and signal_val is not None:
            if histogram > 0 and macd_val > signal_val:
                scores.append(0.7)
                reasons.append("MACD bullish crossover")
            elif histogram < 0 and macd_val < signal_val:
                scores.append(-0.7)
                reasons.append("MACD bearish crossover")
            else:
                scores.append(0.0)

        # ── Bollinger Bands ──
        bb = self.ta.bollinger_bands(closes)
        if bb:
            if bb["current_price"] < bb["lower"]:
                scores.append(0.6)
                reasons.append("Price below lower Bollinger Band")
            elif bb["current_price"] > bb["upper"]:
                scores.append(-0.6)
                reasons.append("Price above upper Bollinger Band")
            if bb["bandwidth"] < 2:
                reasons.append("Low volatility - squeeze forming")

        # ── Volume Analysis ──
        vol = self.ta.volume_analysis(volumes)
        if vol:
            if vol["is_high_volume"]:
                reasons.append(f"High volume ({vol['ratio']:.1f}x avg)")
                # High volume amplifies existing signal
                if scores and scores[-1] > 0:
                    scores[-1] *= 1.3
                elif scores and scores[-1] < 0:
                    scores[-1] *= 1.3

        # ── Order Book Imbalance ──
        if orderbook and orderbook.get("bids") and orderbook.get("asks"):
            bid_vol = sum(q for _, q in orderbook["bids"][:10])
            ask_vol = sum(q for _, q in orderbook["asks"][:10])
            if bid_vol + ask_vol > 0:
                imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol)
                if imbalance > 0.2:
                    scores.append(0.4)
                    reasons.append(f"Order book: buy pressure ({imbalance:.2f})")
                elif imbalance < -0.2:
                    scores.append(-0.4)
                    reasons.append(f"Order book: sell pressure ({imbalance:.2f})")

        # ── Sentiment ──
        if sentiment:
            sent_score = (sentiment.get("sentiment_up", 50) - 50) / 50
            if abs(sent_score) > 0.2:
                scores.append(sent_score * 0.3)
                reasons.append(f"Sentiment: {sentiment.get('sentiment_up', 50)}% bullish")

        # ── Composite Score ──
        if not scores:
            return TradeSignal(Signal.HOLD, 0.0, ["No clear signal"])

        avg_score = np.mean(scores)
        confidence = min(abs(avg_score), 1.0)

        if avg_score > 0.5:
            signal = Signal.STRONG_BUY if avg_score > 0.7 else Signal.BUY
        elif avg_score < -0.5:
            signal = Signal.STRONG_SELL if avg_score < -0.7 else Signal.SELL
        else:
            signal = Signal.HOLD

        return TradeSignal(
            signal=signal,
            confidence=confidence,
            reasons=reasons,
            symbol=klines[0].get("symbol", "UNKNOWN") if klines else "UNKNOWN",
            price=current_price
        )

    def calculate_position_size(self, price: float, max_bnb: float, stop_loss_pct: float) -> float:
        """Calculate position size based on risk management."""
        return max_bnb / price  # Simple: spend max_bnb worth

    def check_exit_conditions(self, position: Position, current_price: float) -> Optional[str]:
        """Check if position should be closed."""
        position.update_pnl(current_price)
        if position.pnl <= -position.stop_loss:
            return "STOP_LOSS"
        if position.pnl >= position.take_profit:
            return "TAKE_PROFIT"
        return None
