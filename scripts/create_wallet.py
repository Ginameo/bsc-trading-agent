#!/usr/bin/env python3
from web3 import Web3
from eth_account import Account
import json

acct = Account.create()
wallet = {
    "address": acct.address,
    "private_key": acct._private_key.hex(),
    "created_at": "2026-06-13"
}

with open("config/wallet.json", "w") as f:
    json.dump(wallet, f, indent=2)

print(f"Address: {wallet['address']}")
print("Private key saved to config/wallet.json")
