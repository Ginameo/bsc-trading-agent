"""
BSC AI Trading Agent - Main Loop
=================================
Autonomous trading agent running on BNB Chain.
Combines multi-signal analysis with on-chain execution.
"""
import time
import json
import signal
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data.market_data import MarketDataFetcher
from src.strategies.engine import TradingStrategy, Signal, Position
from src.execution.executor import BSCExecutor
from config.settings import (
    MAX_TRADE_SIZE_BNB, STOP_LOSS_PCT, TAKE_PROFIT_PCT,
    MAX_OPEN_POSITIONS, MIN_CONFIDENCE_SCORE, BSC_TOKENS
)


class TradingAgent:
    """Autonomous AI Trading Agent for BNB Chain."""

    def __init__(self, live: bool = False):
        self.fetcher = MarketDataFetcher()
        self.strategy = TradingStrategy()
        self.executor = BSCExecutor()
        self.live = live  # False = paper trading, True = real trades
        self.running = True
        self.trade_log = []
        self.stats = {
            "total_signals": 0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "started_at": datetime.utcnow().isoformat()
        }

        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, signum, frame):
        print("\n[Agent] Shutting down gracefully...")
        self.running = False

    def run_cycle(self) -> dict:
        """Run one analysis + trading cycle."""
        cycle_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "signals": [],
            "trades": [],
            "portfolio": {}
        }

        # Analyze BNB/USDT
        print("[Agent] Fetching market data...")
        klines = self.fetcher.get_klines("BNBUSDT", "1h", 100)
        orderbook = self.fetcher.get_orderbook("BNBUSDT")
        sentiment = self.fetcher.get_market_data("binancecoin")

        if not klines:
            print("[Agent] No data available, skipping cycle")
            return cycle_result

        # Run strategy
        print("[Agent] Running strategy analysis...")
        signal_result = self.strategy.analyze(klines, orderbook, sentiment)
        self.stats["total_signals"] += 1
        cycle_result["signals"].append({
            "symbol": "BNBUSDT",
            "signal": signal_result.signal.value,
            "confidence": signal_result.confidence,
            "reasons": signal_result.reasons,
            "price": signal_result.price
        })

        print(f"[Agent] Signal: {signal_result.signal.value} "
              f"(confidence: {signal_result.confidence:.2f})")
        for r in signal_result.reasons:
            print(f"  • {r}")

        # Execute trade if conditions met
        if (signal_result.signal in [Signal.BUY, Signal.STRONG_BUY]
            and signal_result.confidence >= MIN_CONFIDENCE_SCORE
            and len(self.strategy.open_positions) < MAX_OPEN_POSITIONS):

            current_price = self.fetcher.get_price("BNBUSDT")
            if current_price:
                trade_size = min(MAX_TRADE_SIZE_BNB, self.executor.get_balance_bnb() * 0.3)
                if trade_size > 0.001:  # Min trade size
                    if self.live:
                        print(f"[Agent] LIVE TRADE: Buying ${trade_size:.4f} BNB worth")
                        tx_hash = self.executor.buy_token(BSC_TOKENS["WBNB"], trade_size)
                        if tx_hash:
                            self.stats["total_trades"] += 1
                            cycle_result["trades"].append({
                                "type": "BUY",
                                "amount_bnb": trade_size,
                                "tx_hash": tx_hash,
                                "price": current_price
                            })
                    else:
                        print(f"[Agent] PAPER TRADE: Would buy ${trade_size:.4f} BNB worth")
                        self.stats["total_trades"] += 1
                        cycle_result["trades"].append({
                            "type": "PAPER_BUY",
                            "amount_bnb": trade_size,
                            "price": current_price
                        })

        # Check existing positions for exits
        for pos in self.strategy.open_positions[:]:
            current_price = self.fetcher.get_price(pos.symbol)
            if current_price:
                exit_reason = self.strategy.check_exit_conditions(pos, current_price)
                if exit_reason:
                    print(f"[Agent] Exit signal: {exit_reason} for {pos.symbol}")
                    if exit_reason == "TAKE_PROFIT":
                        self.stats["winning_trades"] += 1
                    else:
                        self.stats["losing_trades"] += 1

        # Portfolio status
        if self.executor.is_connected:
            cycle_result["portfolio"] = {
                "bnb_balance": self.executor.get_balance_bnb(),
                "mode": "LIVE" if self.live else "PAPER"
            }

        return cycle_result

    def run(self, interval_seconds: int = 60):
        """Run the agent in a loop."""
        mode = "🔴 LIVE" if self.live else "📝 PAPER"
        print(f"\n{'='*50}")
        print(f"BSC AI Trading Agent - {mode} MODE")
        print(f"{'='*50}")
        print(f"Wallet: {self.executor.wallet_address}")
        print(f"Trade Size: {MAX_TRADE_SIZE_BNB} BNB")
        print(f"Stop Loss: {STOP_LOSS_PCT}%")
        print(f"Take Profit: {TAKE_PROFIT_PCT}%")
        print(f"Cycle Interval: {interval_seconds}s")
        print(f"{'='*50}\n")

        cycle_count = 0
        while self.running:
            cycle_count += 1
            print(f"\n--- Cycle #{cycle_count} ---")
            try:
                result = self.run_cycle()
                self.trade_log.append(result)
            except Exception as e:
                print(f"[Agent] Error in cycle: {e}")

            if self.running:
                time.sleep(interval_seconds)

        # Final report
        print(f"\n{'='*50}")
        print("Agent Stopped - Final Report")
        print(f"{'='*50}")
        print(f"Total Signals: {self.stats['total_signals']}")
        print(f"Total Trades: {self.stats['total_trades']}")
        print(f"Winning: {self.stats['winning_trades']}")
        print(f"Losing: {self.stats['losing_trades']}")
        print(f"Runtime: {self.stats['started_at']} to {datetime.utcnow().isoformat()}")

    def get_status(self) -> dict:
        """Get current agent status for dashboard."""
        return {
            "running": self.running,
            "mode": "LIVE" if self.live else "PAPER",
            "stats": self.stats,
            "open_positions": len(self.strategy.open_positions),
            "wallet": self.executor.wallet_address,
            "balance_bnb": self.executor.get_balance_bnb() if self.executor.is_connected else 0,
            "recent_trades": self.trade_log[-5:] if self.trade_log else []
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="BSC AI Trading Agent")
    parser.add_argument("--live", action="store_true", help="Enable live trading")
    parser.add_argument("--interval", type=int, default=60, help="Cycle interval in seconds")
    args = parser.parse_args()

    agent = TradingAgent(live=args.live)
    agent.run(interval_seconds=args.interval)
