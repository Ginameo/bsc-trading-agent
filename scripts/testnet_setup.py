#!/usr/bin/env python3
"""
Testnet Setup Script
====================
Run this after getting tBNB from faucet.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Switch to testnet
os.environ["BSC_RPC_URL"] = "https://data-seed-prebsc-1-s1.binance.org:8545/"
os.environ["BSC_CHAIN_ID"] = "97"

from web3 import Web3
from eth_account import Account

WALLET_PRIVATE_KEY = "31b760e0d595dbae6ebba213016352d6f92f247b007d8abda51c7982df8bc199"
WALLET_ADDRESS = "0x6D89b06649830B86a72b4385f9703d3B4bdb174b"

w3 = Web3(Web3.HTTPProvider("https://data-seed-prebsc-1-s1.binance.org:8545/"))
account = Account.from_key(WALLET_PRIVATE_KEY)

print("=== BSC Testnet Setup ===\n")
print(f"Connected: {w3.is_connected()}")
print(f"Chain ID: {w3.eth.chain_id}")
print(f"Wallet: {account.address}")

balance = w3.eth.get_balance(account.address)
balance_bnb = float(w3.from_wei(balance, 'ether'))
print(f"Balance: {balance_bnb:.4f} tBNB")

if balance_bnb < 0.01:
    print("\n⚠️ Need tBNB! Go to:")
    print("https://www.bnbchain.org/en/testnet-faucet")
    print(f"Send tBNB to: {account.address}")
else:
    print("\n✅ Ready for testnet registration!")

    # Test registration contract
    print("\nCompetition contract (testnet):")
    print("0x212c61b9b72c95d95b129c1032f5e5635629aed5")
    print("\nRun: python3 src/competition.py")
