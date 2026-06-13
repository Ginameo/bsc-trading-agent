"""
On-Chain Execution Layer
========================
Execute trades on BSC via PancakeSwap router.
"""
import json
import time
from web3 import Web3
from typing import Optional, Dict
from eth_account import Account
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    BSC_RPC_URL, BSC_CHAIN_ID, WALLET_ADDRESS, WALLET_PRIVATE_KEY,
    PANCAKE_ROUTER, BSC_TOKENS, MAX_TRADE_SIZE_BNB
)

# PancakeSwap Router V2 ABI (minimal)
ROUTER_ABI = json.loads('''[
    {
        "name": "swapExactETHForTokens",
        "type": "function",
        "stateMutability": "payable",
        "inputs": [
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "outputs": [{"name": "amounts", "type": "uint256[]"}]
    },
    {
        "name": "swapExactTokensForETH",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "outputs": [{"name": "amounts", "type": "uint256[]"}]
    },
    {
        "name": "getAmountsOut",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "path", "type": "address[]"}
        ],
        "outputs": [{"name": "amounts", "type": "uint256[]"}]
    },
    {
        "name": "WETH",
        "type": "function",
        "stateMutability": "pure",
        "inputs": [],
        "outputs": [{"name": "", "type": "address"}]
    }
]''')

ERC20_ABI = json.loads('''[
    {
        "name": "balanceOf",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}]
    },
    {
        "name": "decimals",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint8"}]
    },
    {
        "name": "approve",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "outputs": [{"name": "", "type": "bool"}]
    },
    {
        "name": "allowance",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "outputs": [{"name": "", "type": "uint256"}]
    }
]''')


class BSCExecutor:
    """Execute trades on BSC via PancakeSwap."""

    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(BSC_RPC_URL))
        self.account = Account.from_key(WALLET_PRIVATE_KEY) if WALLET_PRIVATE_KEY != "REPLACE_WITH_KEY_FROM_CONFIG_WALLET_JSON" else None
        self.router = self.w3.eth.contract(
            address=Web3.to_checksum_address(PANCAKE_ROUTER),
            abi=ROUTER_ABI
        )
        self.wbnb = Web3.to_checksum_address(BSC_TOKENS["WBNB"])
        self.pending_txs = []

    @property
    def is_connected(self) -> bool:
        return self.w3.is_connected()

    @property
    def wallet_address(self) -> str:
        return self.account.address if self.account else WALLET_ADDRESS

    def get_balance_bnb(self) -> float:
        """Get BNB balance."""
        balance = self.w3.eth.get_balance(Web3.to_checksum_address(self.wallet_address))
        return float(self.w3.from_wei(balance, 'ether'))

    def get_token_balance(self, token_address: str) -> float:
        """Get ERC20 token balance."""
        token = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
        decimals = token.functions.decimals().call()
        balance = token.functions.balanceOf(Web3.to_checksum_address(self.wallet_address)).call()
        return balance / (10 ** decimals)

    def get_quote(self, amount_in_bnb: float, token_address: str) -> Optional[float]:
        """Get expected output amount for a swap."""
        try:
            amount_in_wei = self.w3.to_wei(amount_in_bnb, 'ether')
            path = [self.wbnb, Web3.to_checksum_address(token_address)]
            amounts = self.router.functions.getAmountsOut(amount_in_wei, path).call()
            token = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            decimals = token.functions.decimals().call()
            return amounts[-1] / (10 ** decimals)
        except Exception as e:
            print(f"[Executor] Quote error: {e}")
            return None

    def buy_token(self, token_address: str, amount_bnb: float, slippage: float = 0.05) -> Optional[str]:
        """Buy token with BNB via PancakeSwap."""
        if not self.account:
            print("[Executor] No wallet configured")
            return None

        try:
            amount_in_wei = self.w3.to_wei(amount_bnb, 'ether')

            # Get expected output
            path = [self.wbnb, Web3.to_checksum_address(token_address)]
            amounts = self.router.functions.getAmountsOut(amount_in_wei, path).call()
            min_out = int(amounts[-1] * (1 - slippage))

            # Build transaction
            deadline = int(time.time()) + 300  # 5 min deadline
            tx = self.router.functions.swapExactETHForTokens(
                min_out,
                path,
                Web3.to_checksum_address(self.wallet_address),
                deadline
            ).build_transaction({
                'from': Web3.to_checksum_address(self.wallet_address),
                'value': amount_in_wei,
                'gas': 250000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(
                    Web3.to_checksum_address(self.wallet_address)
                ),
                'chainId': BSC_CHAIN_ID
            })

            # Sign and send
            signed = self.w3.eth.account.sign_transaction(tx, WALLET_PRIVATE_KEY)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"[Executor] Buy tx sent: {tx_hash.hex()}")
            return tx_hash.hex()

        except Exception as e:
            print(f"[Executor] Buy error: {e}")
            return None

    def sell_token(self, token_address: str, amount_tokens: float, slippage: float = 0.05) -> Optional[str]:
        """Sell token for BNB via PancakeSwap."""
        if not self.account:
            print("[Executor] No wallet configured")
            return None

        try:
            token = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            decimals = token.functions.decimals().call()
            amount_in = int(amount_tokens * (10 ** decimals))

            # Get expected BNB output
            path = [Web3.to_checksum_address(token_address), self.wbnb]
            amounts = self.router.functions.getAmountsOut(amount_in, path).call()
            min_out = int(amounts[-1] * (1 - slippage))

            # Approve if needed
            allowance = token.functions.allowance(
                Web3.to_checksum_address(self.wallet_address),
                Web3.to_checksum_address(PANCAKE_ROUTER)
            ).call()
            if allowance < amount_in:
                approve_tx = token.functions.approve(
                    Web3.to_checksum_address(PANCAKE_ROUTER),
                    2**256 - 1  # Max approval
                ).build_transaction({
                    'from': Web3.to_checksum_address(self.wallet_address),
                    'gas': 60000,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(
                        Web3.to_checksum_address(self.wallet_address)
                    ),
                    'chainId': BSC_CHAIN_ID
                })
                signed = self.w3.eth.account.sign_transaction(approve_tx, WALLET_PRIVATE_KEY)
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                print(f"[Executor] Approve tx: {tx_hash.hex()}")
                self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            # Build sell transaction
            deadline = int(time.time()) + 300
            tx = self.router.functions.swapExactTokensForETH(
                amount_in,
                min_out,
                path,
                Web3.to_checksum_address(self.wallet_address),
                deadline
            ).build_transaction({
                'from': Web3.to_checksum_address(self.wallet_address),
                'gas': 250000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(
                    Web3.to_checksum_address(self.wallet_address)
                ),
                'chainId': BSC_CHAIN_ID
            })

            signed = self.w3.eth.account.sign_transaction(tx, WALLET_PRIVATE_KEY)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"[Executor] Sell tx sent: {tx_hash.hex()}")
            return tx_hash.hex()

        except Exception as e:
            print(f"[Executor] Sell error: {e}")
            return None

    def get_portfolio(self) -> dict:
        """Get current portfolio status."""
        portfolio = {
            "bnb_balance": self.get_balance_bnb(),
            "tokens": {},
            "total_value_bnb": 0
        }
        for name, addr in BSC_TOKENS.items():
            if name == "WBNB":
                continue
            try:
                balance = self.get_token_balance(addr)
                if balance > 0:
                    portfolio["tokens"][name] = {
                        "address": addr,
                        "balance": balance
                    }
            except:
                pass
        portfolio["total_value_bnb"] = portfolio["bnb_balance"]
        return portfolio


if __name__ == "__main__":
    executor = BSCExecutor()
    print("=== BSC Trading Agent - Executor Test ===\n")

    if executor.is_connected:
        print(f"✅ Connected to BSC")
        print(f"Wallet: {executor.wallet_address}")
        balance = executor.get_balance_bnb()
        print(f"BNB Balance: {balance:.4f}")

        # Test quote
        quote = executor.get_quote(0.01, BSC_TOKENS["CAKE"])
        if quote:
            print(f"Quote: 0.01 BNB -> {quote:.4f} CAKE")
    else:
        print("❌ Not connected to BSC")
