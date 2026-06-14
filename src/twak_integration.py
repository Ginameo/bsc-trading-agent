"""
Trust Wallet Agent Kit (TWAK) Integration
==========================================
Uses TWAK CLI for self-custody swaps, price queries, and competition registration.
"""
import json
import subprocess
import os
import sys
from typing import Optional, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TWAK_BIN = "twak"
WALLET_PASSWORD = os.getenv("TWAK_WALLET_PASSWORD", "bsc-agent-2026")


def _run_twak(args: List[str], timeout: int = 30) -> Optional[dict]:
    """Run a TWAK CLI command and return parsed JSON output."""
    cmd = [TWAK_BIN] + args + ["--json", "--no-analytics"]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "TWAK_WALLET_PASSWORD": WALLET_PASSWORD}
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        elif result.stderr:
            print(f"[TWAK] stderr: {result.stderr[:200]}")
        return None
    except subprocess.TimeoutExpired:
        print(f"[TWAK] Command timed out: {' '.join(args)}")
        return None
    except json.JSONDecodeError:
        # Some commands return non-JSON
        return {"raw": result.stdout} if result else None
    except Exception as e:
        print(f"[TWAK] Error: {e}")
        return None


def get_price(token: str) -> Optional[float]:
    """Get token price via TWAK."""
    data = _run_twak(["price", token])
    if data and "price" in data:
        return float(data["price"])
    return None


def get_balance(token: str = "BNB", chain: str = "bsc") -> Optional[float]:
    """Get token balance via TWAK."""
    data = _run_twak(["balance", "--chain", chain, "--token", token])
    if data and "balance" in data:
        return float(data["balance"])
    return None


def swap(amount: float, from_token: str, to_token: str, chain: str = "bsc") -> Optional[dict]:
    """Execute a token swap via TWAK."""
    data = _run_twak([
        "swap", str(amount), from_token, to_token,
        "--chain", chain
    ], timeout=60)
    return data


def get_swap_quote(amount: float, from_token: str, to_token: str, chain: str = "bsc") -> Optional[dict]:
    """Get swap quote without executing."""
    data = _run_twak([
        "swap", "--quote-only", str(amount), from_token, to_token,
        "--chain", chain
    ])
    return data


def search_tokens(query: str) -> Optional[List[dict]]:
    """Search for tokens via TWAK."""
    data = _run_twak(["search", query])
    if data and "results" in data:
        return data["results"]
    return []


def get_trending() -> Optional[List[dict]]:
    """Get trending tokens via TWAK."""
    data = _run_twak(["trending"])
    return data


def check_risk(token_id: str) -> Optional[dict]:
    """Check token risk/safety via TWAK."""
    data = _run_twak(["risk", token_id])
    return data


def get_tx_history(chain: str = "bsc") -> Optional[List[dict]]:
    """Get transaction history."""
    data = _run_twak(["history", "--chain", chain])
    return data


def register_competition() -> Optional[dict]:
    """Register for BNB Hack competition via TWAK."""
    data = _run_twak(["compete", "register", "--password", WALLET_PASSWORD], timeout=60)
    return data


def competition_status() -> Optional[dict]:
    """Check competition registration status."""
    data = _run_twak(["compete", "status"])
    return data


def setup_wallet(private_key: str) -> bool:
    """Setup TWAK wallet with our private key."""
    try:
        # Import wallet
        result = subprocess.run(
            [TWAK_BIN, "wallet", "import", "--private-key", private_key,
             "--password", WALLET_PASSWORD, "--no-analytics"],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[TWAK] Wallet setup error: {e}")
        return False


if __name__ == "__main__":
    print("=== TWAK Integration Test ===\n")

    # Test price
    price = get_price("BNB")
    if price:
        print(f"BNB Price (TWAK): ${price}")
    else:
        print("BNB Price: Could not fetch")

    # Test trending
    trending = get_trending()
    if trending:
        print(f"Trending: {json.dumps(trending, indent=2)[:200]}")

    # Check competition status
    status = competition_status()
    if status:
        print(f"Competition: {json.dumps(status, indent=2)}")

    print("\n✅ TWAK integration ready")
