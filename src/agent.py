"""
BSC AI Trading Agent - Main Loop (v2 - Competition Ready)
==========================================================
Integrates: BNB Agent SDK, TWAK, Risk Management, Multi-pair trading.
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
from src.risk_manager import RiskManager, RiskConfig
from src.competition import (
    TRADING_PAIRS, ELIGIBLE_TOKENS, register_agent_on_chain,
    is_eligible_token, get_eligible_token_address
)
from src.cmc_agent_hub import CMCAgentHub
from config.settings import (
    MAX_TRADE_SIZE_BNB, STOP_LOSS_PCT, TAKE_PROFIT_PCT,
    MAX_OPEN_POSITIONS, MIN_CONFIDENCE_SCORE, BSC_TOKENS
)


class TradingAgent:
    """Autonomous AI Trading Agent for BNB Hack competition."""

    def __init__(self, live: bool = False):
        self.fetcher = MarketDataFetcher()
        self.strategy = TradingStrategy()
        self.executor = BSCExecutor()
        self.cmc = CMCAgentHub()  # CMC Agent Hub integration
        self.risk_manager = RiskManager(RiskConfig(
            max_drawdown_pct=30.0,
            stop_loss_pct=STOP_LOSS_PCT,
            take_profit_pct=TAKE_PROFIT_PCT,
            max_position_size_bnb=MAX_TRADE_SIZE_BNB,
            max_open_positions=MAX_OPEN_POSITIONS,
            min_trades_per_day=1
        ))
        self.live = live
        self.running = True
        self.trade_log = []
        self.current_pair_index = 0
        self.stats = {
            "total_signals": 0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "started_at": datetime.utcnow().isoformat(),
            "pairs_traded": []
        }

        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, signum, frame):
        print("\n[Agent] Shutting down gracefully...")
        self.running = False

    def _get_next_pair(self) -> str:
        """Rotate through trading pairs."""
        pair = TRADING_PAIRS[self.current_pair_index]
        self.current_pair_index = (self.current_pair_index + 1) % len(TRADING_PAIRS)
        return pair

    def run_cycle(self) -> dict:
        """Run one analysis + trading cycle across multiple pairs."""
        cycle_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "signals": [],
            "trades": [],
            "risk": self.risk_manager.get_stats()
        }

        # Check if we can trade
        can_trade, reason = self.risk_manager.can_trade()
        if not can_trade:
            print(f"[Agent] Trading blocked: {reason}")
            cycle_result["blocked_reason"] = reason
            return cycle_result

        # Check if we need more trades today
        needs_trades = self.risk_manager.needs_more_trades()
        if needs_trades:
            print("[Agent] ⚡ Need to meet min 1 trade/day requirement")

        # Get CMC Agent Hub sentiment
        cmc_sentiment = self.cmc.get_market_sentiment()
        if cmc_sentiment:
            fng = cmc_sentiment.get("fear_greed_index", 50)
            classification = cmc_sentiment.get("classification", "Neutral")
            print(f"[CMC] Fear & Greed: {fng} ({classification})")
            cycle_result["cmc_sentiment"] = cmc_sentiment

        # Analyze 3 pairs per cycle
        for _ in range(3):
            pair = self._get_next_pair()
            symbol = pair.replace("USDT", "")
            coin_id = self._symbol_to_coingecko_id(symbol)

            print(f"\n[Agent] Analyzing {pair}...")
            klines = self.fetcher.get_klines(pair, "1h", 100)
            if not klines:
                continue

            orderbook = self.fetcher.get_orderbook(pair)
            sentiment = self.fetcher.get_market_data(coin_id) if coin_id else {}

            signal_result = self.strategy.analyze(klines, orderbook, sentiment or {})
            self.stats["total_signals"] += 1

            cycle_result["signals"].append({
                "symbol": pair,
                "signal": signal_result.signal.value,
                "confidence": signal_result.confidence,
                "reasons": signal_result.reasons,
                "price": signal_result.price
            })

            print(f"[Agent] {pair}: {signal_result.signal.value} "
                  f"(confidence: {signal_result.confidence:.2f})")

            # Execute if conditions met
            if (signal_result.signal in [Signal.BUY, Signal.STRONG_BUY]
                and signal_result.confidence >= MIN_CONFIDENCE_SCORE):

                current_price = self.fetcher.get_price(pair)
                if current_price:
                    position_size = self.risk_manager.get_position_size(current_price)
                    trade_size = min(position_size, self.executor.get_balance_bnb() * 0.3)

                    if trade_size > 0.001:
                        token_addr = get_eligible_token_address(symbol)
                        if not token_addr:
                            token_addr = BSC_TOKENS.get(symbol)

                        if token_addr:
                            if self.live:
                                print(f"[Agent] LIVE TRADE: Buying {trade_size:.4f} BNB of {symbol}")
                                tx_hash = self.executor.buy_token(token_addr, trade_size)
                                if tx_hash:
                                    self.stats["total_trades"] += 1
                                    self.risk_manager.record_trade(0, True)
                                    cycle_result["trades"].append({
                                        "type": "BUY", "symbol": pair,
                                        "amount_bnb": trade_size, "tx_hash": tx_hash
                                    })
                            else:
                                print(f"[Agent] PAPER TRADE: Would buy {trade_size:.4f} BNB of {symbol}")
                                self.stats["total_trades"] += 1
                                self.risk_manager.record_trade(0, True)
                                cycle_result["trades"].append({
                                    "type": "PAPER_BUY", "symbol": pair,
                                    "amount_bnb": trade_size
                                })

                            if pair not in self.stats["pairs_traded"]:
                                self.stats["pairs_traded"].append(pair)

        # Update balance
        if self.executor.is_connected:
            balance = self.executor.get_balance_bnb()
            self.risk_manager.update_balance(balance)
            cycle_result["balance"] = balance

        return cycle_result

    def _symbol_to_coingecko_id(self, symbol: str) -> str:
        """Map symbol to CoinGecko ID."""
        mapping = {
            "BNB": "binancecoin", "ETH": "ethereum", "XRP": "ripple",
            "ADA": "cardano", "DOGE": "dogecoin", "CAKE": "pancakeswap-token",
            "LINK": "chainlink", "DOT": "polkadot", "UNI": "uniswap",
            "LTC": "litecoin", "AVAX": "avalanche-2", "ATOM": "cosmos",
            "SHIB": "shiba-inu", "FIL": "filecoin", "INJ": "injective-protocol"
        }
        return mapping.get(symbol, "")

    def run(self, interval_seconds: int = 120):
        """Run the agent in a loop."""
        mode = "🔴 LIVE" if self.live else "📝 PAPER"
        print(f"\n{'='*60}")
        print(f"BSC AI Trading Agent v2 - {mode} MODE")
        print(f"BNB Hack: AI Trading Agent Edition")
        print(f"{'='*60}")
        print(f"Wallet: {self.executor.wallet_address}")
        print(f"Trading Pairs: {len(TRADING_PAIRS)}")
        print(f"Max Drawdown: {self.risk_manager.config.max_drawdown_pct}%")
        print(f"Min Trades/Day: {self.risk_manager.config.min_trades_per_day}")
        print(f"Cycle Interval: {interval_seconds}s")
        print(f"{'='*60}\n")

        # Initialize risk manager with current balance
        if self.executor.is_connected:
            balance = self.executor.get_balance_bnb()
            self.risk_manager.initialize(balance)
            print(f"[Agent] Balance: {balance:.4f} BNB")

        cycle_count = 0
        while self.running:
            cycle_count += 1
            print(f"\n--- Cycle #{cycle_count} ---")
            try:
                result = self.run_cycle()
                self.trade_log.append(result)

                # Print risk status
                risk = result.get("risk", {})
                print(f"[Risk] Drawdown: {risk.get('drawdown_pct', 0)}% | "
                      f"Trades today: {risk.get('daily_trades', 0)} | "
                      f"Win rate: {risk.get('win_rate', 0)}%")

            except Exception as e:
                print(f"[Agent] Error: {e}")

            if self.running:
                time.sleep(interval_seconds)

        # Final report
        print(f"\n{'='*60}")
        print("Agent Stopped - Final Report")
        print(f"{'='*60}")
        risk_stats = self.risk_manager.get_stats()
        print(f"Total Signals: {self.stats['total_signals']}")
        print(f"Total Trades: {self.stats['total_trades']}")
        print(f"Win Rate: {risk_stats['win_rate']}%")
        print(f"Max Drawdown: {risk_stats['drawdown_pct']}%")
        print(f"Pairs Traded: {', '.join(self.stats['pairs_traded'])}")

    def get_status(self) -> dict:
        """Get current agent status."""
        return {
            "running": self.running,
            "mode": "LIVE" if self.live else "PAPER",
            "stats": self.stats,
            "risk": self.risk_manager.get_stats(),
            "wallet": self.executor.wallet_address,
            "balance_bnb": self.executor.get_balance_bnb() if self.executor.is_connected else 0
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="BSC AI Trading Agent v2")
    parser.add_argument("--live", action="store_true", help="Enable live trading")
    parser.add_argument("--interval", type=int, default=120, help="Cycle interval (seconds)")
    parser.add_argument("--register", action="store_true", help="Register agent on-chain first")
    args = parser.parse_args()

    if args.register:
        print("Registering agent on-chain...")
        result = register_agent_on_chain()
        if result:
            print(f"✅ Registered: {result}")
        else:
            print("⚠️ Registration failed")

    agent = TradingAgent(live=args.live)
    agent.run(interval_seconds=args.interval)
