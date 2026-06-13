"""
Backtesting Engine
==================
Test strategies against historical data before going live.
"""
import json
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.strategies.engine import TradingStrategy, TradeSignal, Signal, Position
from src.data.market_data import MarketDataFetcher


@dataclass
class BacktestResult:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    trades: List[dict] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"Backtest Results\n"
            f"{'='*40}\n"
            f"Total Trades:    {self.total_trades}\n"
            f"Winning Trades:  {self.winning_trades}\n"
            f"Losing Trades:   {self.losing_trades}\n"
            f"Win Rate:        {self.win_rate:.1f}%\n"
            f"Total PnL:       {self.total_pnl_pct:+.2f}%\n"
            f"Max Drawdown:    {self.max_drawdown_pct:.2f}%\n"
            f"Sharpe Ratio:    {self.sharpe_ratio:.2f}\n"
        )


class Backtester:
    """Run backtests on historical candle data."""

    def __init__(self, initial_capital: float = 1.0):
        self.initial_capital = initial_capital
        self.strategy = TradingStrategy()

    def run(self, klines: List[dict], position_size_pct: float = 0.3,
            stop_loss_pct: float = 3.0, take_profit_pct: float = 5.0) -> BacktestResult:
        """Run backtest on kline data."""
        result = BacktestResult()
        capital = self.initial_capital
        peak_capital = capital
        position = None

        for i in range(26, len(klines)):
            window = klines[:i+1]
            current_price = klines[i]["close"]

            # Check exit if in position
            if position:
                exit_reason = self.strategy.check_exit_conditions(position, current_price)
                if exit_reason:
                    pnl_pct = position.pnl
                    capital *= (1 + pnl_pct / 100)
                    result.total_trades += 1
                    if pnl_pct > 0:
                        result.winning_trades += 1
                    else:
                        result.losing_trades += 1
                    result.trades.append({
                        "type": "CLOSE",
                        "reason": exit_reason,
                        "price": current_price,
                        "pnl_pct": pnl_pct,
                        "capital": capital
                    })
                    position = None

            # Check entry if no position
            if not position:
                signal = self.strategy.analyze(window)
                if signal.signal in [Signal.BUY, Signal.STRONG_BUY] and signal.confidence >= 0.6:
                    amount = (capital * position_size_pct) / current_price
                    position = Position(
                        symbol="BNBUSDT",
                        entry_price=current_price,
                        amount=amount,
                        side="long",
                        stop_loss=stop_loss_pct,
                        take_profit=take_profit_pct,
                        opened_at=klines[i].get("timestamp", "")
                    )
                    result.trades.append({
                        "type": "OPEN",
                        "signal": signal.signal.value,
                        "confidence": signal.confidence,
                        "price": current_price,
                        "reasons": signal.reasons
                    })

            # Track equity
            equity = capital
            if position:
                position.update_pnl(current_price)
                equity = capital * (1 + position.pnl / 100 * (position.amount * current_price / capital))
            result.equity_curve.append(equity)
            peak_capital = max(peak_capital, equity)
            drawdown = (peak_capital - equity) / peak_capital * 100
            result.max_drawdown_pct = max(result.max_drawdown_pct, drawdown)

        # Close any remaining position
        if position:
            current_price = klines[-1]["close"]
            position.update_pnl(current_price)
            capital *= (1 + position.pnl / 100)
            result.total_trades += 1
            if position.pnl > 0:
                result.winning_trades += 1
            else:
                result.losing_trades += 1

        result.total_pnl_pct = (capital - self.initial_capital) / self.initial_capital * 100
        if result.total_trades > 0:
            result.win_rate = result.winning_trades / result.total_trades * 100

        # Calculate Sharpe ratio from equity curve
        if len(result.equity_curve) > 1:
            returns = [(result.equity_curve[i] - result.equity_curve[i-1]) / result.equity_curve[i-1]
                       for i in range(1, len(result.equity_curve))]
            if returns and sum(returns) != 0:
                import numpy as np
                result.sharpe_ratio = np.mean(returns) / (np.std(returns) + 1e-10) * (252 ** 0.5)

        return result


if __name__ == "__main__":
    fetcher = MarketDataFetcher()
    backtester = Backtester(initial_capital=1.0)

    print("=== BSC Trading Agent - Backtest ===\n")
    print("Fetching historical data...")

    klines = fetcher.get_klines("BNBUSDT", "1h", 200)
    if not klines:
        print("❌ Failed to fetch klines")
        exit(1)

    print(f"Got {len(klines)} candles")
    print(f"Period: {klines[0]['timestamp']} to {klines[-1]['timestamp']}")
    print(f"Price range: ${min(k['low'] for k in klines):.2f} - ${max(k['high'] for k in klines):.2f}\n")

    result = backtester.run(klines)
    print(result.summary())

    if result.trades:
        print("Recent Trades:")
        for t in result.trades[-5:]:
            print(f"  {t['type']} @ ${t['price']:.2f} | {t.get('reasons', t.get('reason', ''))}")
