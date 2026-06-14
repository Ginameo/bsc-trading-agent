"""
Risk Management Module
======================
Competition-compliant risk controls:
- 30% max drawdown cap (disqualification threshold)
- Min 1 trade/day (7 over trading week)
- Position sizing with risk limits
- Portfolio monitoring
"""
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class RiskConfig:
    max_drawdown_pct: float = 30.0       # Competition hard cap
    stop_loss_pct: float = 3.0           # Per-trade stop loss
    take_profit_pct: float = 5.0         # Per-trade take profit
    max_position_size_bnb: float = 0.05  # Max per trade
    max_open_positions: int = 3          # Max concurrent
    min_trades_per_day: int = 1          # Competition minimum
    max_daily_loss_pct: float = 10.0     # Daily loss limit
    cooldown_after_loss_seconds: int = 300  # 5 min cooldown after loss


@dataclass
class PortfolioState:
    initial_balance: float = 0.0
    current_balance: float = 0.0
    peak_balance: float = 0.0
    drawdown_pct: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    daily_trades: Dict[str, int] = field(default_factory=dict)
    daily_pnl: Dict[str, float] = field(default_factory=dict)
    last_trade_time: str = ""
    last_loss_time: float = 0.0
    is_active: bool = True
    disqualification_reason: str = ""


class RiskManager:
    """Competition-compliant risk management."""

    def __init__(self, config: RiskConfig = None, state_file: str = "data/portfolio_state.json"):
        self.config = config or RiskConfig()
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self) -> PortfolioState:
        """Load portfolio state from file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    state = PortfolioState()
                    for k, v in data.items():
                        if hasattr(state, k):
                            setattr(state, k, v)
                    return state
        except Exception:
            pass
        return PortfolioState()

    def _save_state(self):
        """Save portfolio state to file."""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(asdict(self.state), f, indent=2)
        except Exception as e:
            print(f"[RiskManager] Save error: {e}")

    def initialize(self, balance: float):
        """Initialize portfolio with starting balance."""
        self.state.initial_balance = balance
        self.state.current_balance = balance
        self.state.peak_balance = balance
        self.state.drawdown_pct = 0.0
        self.state.is_active = True
        self.state.disqualification_reason = ""
        self._save_state()
        print(f"[RiskManager] Initialized with {balance:.4f} BNB")

    def update_balance(self, new_balance: float):
        """Update current balance and recalculate drawdown."""
        self.state.current_balance = new_balance
        if new_balance > self.state.peak_balance:
            self.state.peak_balance = new_balance

        if self.state.peak_balance > 0:
            self.state.drawdown_pct = (
                (self.state.peak_balance - new_balance) / self.state.peak_balance * 100
            )

        # Check drawdown cap
        if self.state.drawdown_pct >= self.config.max_drawdown_pct:
            self.state.is_active = False
            self.state.disqualification_reason = (
                f"Max drawdown exceeded: {self.state.drawdown_pct:.1f}% >= {self.config.max_drawdown_pct}%"
            )
            print(f"[RiskManager] ⚠️ DISQUALIFIED: {self.state.disqualification_reason}")

        self._save_state()

    def can_trade(self) -> tuple[bool, str]:
        """Check if trading is allowed."""
        if not self.state.is_active:
            return False, f"Agent inactive: {self.state.disqualification_reason}"

        # Check cooldown after loss
        if self.state.last_loss_time > 0:
            elapsed = time.time() - self.state.last_loss_time
            if elapsed < self.config.cooldown_after_loss_seconds:
                remaining = self.config.cooldown_after_loss_seconds - elapsed
                return False, f"Cooldown after loss: {remaining:.0f}s remaining"

        # Check daily loss limit
        today = datetime.utcnow().strftime("%Y-%m-%d")
        daily_pnl = self.state.daily_pnl.get(today, 0)
        if daily_pnl < -self.config.max_daily_loss_pct:
            return False, f"Daily loss limit reached: {daily_pnl:.1f}%"

        # Check max positions
        # (This would need position tracking - simplified here)

        return True, "OK"

    def record_trade(self, pnl_pct: float, is_win: bool):
        """Record a trade result."""
        today = datetime.utcnow().strftime("%Y-%m-%d")

        self.state.total_trades += 1
        if is_win:
            self.state.winning_trades += 1
        else:
            self.state.losing_trades += 1
            self.state.last_loss_time = time.time()

        # Track daily trades
        if today not in self.state.daily_trades:
            self.state.daily_trades[today] = 0
        self.state.daily_trades[today] += 1

        # Track daily PnL
        if today not in self.state.daily_pnl:
            self.state.daily_pnl[today] = 0
        self.state.daily_pnl[today] += pnl_pct

        self.state.last_trade_time = datetime.utcnow().isoformat()
        self._save_state()

    def get_position_size(self, price: float) -> float:
        """Calculate safe position size based on risk limits."""
        max_size = self.config.max_position_size_bnb
        # Reduce size after losses
        if self.state.losing_trades > 0 and self.state.total_trades > 0:
            loss_ratio = self.state.losing_trades / self.state.total_trades
            if loss_ratio > 0.5:
                max_size *= 0.5  # Half size after >50% loss rate
        return max_size

    def needs_more_trades(self) -> bool:
        """Check if we need more trades to meet minimum."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        daily_count = self.state.daily_trades.get(today, 0)
        return daily_count < self.config.min_trades_per_day

    def get_stats(self) -> dict:
        """Get current risk stats."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        win_rate = (
            self.state.winning_trades / self.state.total_trades * 100
            if self.state.total_trades > 0 else 0
        )
        return {
            "is_active": self.state.is_active,
            "drawdown_pct": round(self.state.drawdown_pct, 2),
            "max_drawdown_pct": self.config.max_drawdown_pct,
            "total_trades": self.state.total_trades,
            "win_rate": round(win_rate, 1),
            "daily_trades": self.state.daily_trades.get(today, 0),
            "min_daily_trades": self.config.min_trades_per_day,
            "daily_pnl": round(self.state.daily_pnl.get(today, 0), 2),
            "disqualification_reason": self.state.disqualification_reason
        }


if __name__ == "__main__":
    rm = RiskManager()
    rm.initialize(0.1)  # 0.1 BNB starting balance

    stats = rm.get_stats()
    print("=== Risk Manager Status ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    can, reason = rm.can_trade()
    print(f"\nCan trade: {can} ({reason})")
    print(f"Needs more trades: {rm.needs_more_trades()}")
