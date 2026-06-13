"""
Configuration Settings
======================
"""
import os
from dotenv import load_dotenv

load_dotenv()

# BSC Network
BSC_RPC_URL = os.getenv("BSC_RPC_URL", "https://bsc-dataseed1.binance.org/")
BSC_CHAIN_ID = int(os.getenv("BSC_CHAIN_ID", "56"))

# Wallet
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "")
WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY", "")

# Trading Parameters
MAX_TRADE_SIZE_BNB = float(os.getenv("MAX_TRADE_SIZE_BNB", "0.01"))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "3.0"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "5.0"))
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "3"))
MIN_CONFIDENCE_SCORE = float(os.getenv("MIN_CONFIDENCE_SCORE", "0.7"))

# API Endpoints
BINANCE_API_URL = os.getenv("BINANCE_API_URL", "https://api.binance.com")
COINGECKO_API_URL = os.getenv("COINGECKO_API_URL", "https://api.coingecko.com/api/v3")
DEXSCREENER_API_URL = os.getenv("DEXSCREENER_API_URL", "https://api.dexscreener.com/latest")

# Dashboard
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))

# BSC Contract Addresses (commonly traded)
BSC_TOKENS = {
    "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
    "BUSD": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
    "USDT": "0x55d398326f99059fF775485246999027B3197955",
    "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
    "CAKE": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",
    "XRP": "0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE",
    "ADA": "0x3EE2200Efb3400fAbB9AacF31297cBdD1d435D47",
    "DOGE": "0xbA2aE424d960c26247Dd6c32edC70B295c744C43",
}

# PancakeSwap Router (BSC DEX)
PANCAKE_ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
PANCAKE_FACTORY = "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"
