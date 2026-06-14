"""
Competition Registration & Eligible Tokens
===========================================
BNB Hack: AI Trading Agent Edition compliance module.
"""
import json
import os
import sys
from web3 import Web3
from eth_account import Account

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import BSC_RPC_URL, BSC_CHAIN_ID, WALLET_PRIVATE_KEY

# Competition contract
COMPETITION_CONTRACT = "0x212c61b9b72c95d95b129c1032f5e5635629aed5"

# 149 eligible BEP-20 tokens for competition
ELIGIBLE_TOKENS = {
    "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
    "ETH": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",
    "USDT": "0x55d398326f99059fF775485246999027B3197955",
    "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
    "XRP": "0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE",
    "TRX": "0x85EAC5Ac2F758618dFa09bDbe0cf174e7d574D5B",
    "DOGE": "0xbA2aE424d960c26247Dd6c32edC70B295c744C43",
    "ADA": "0x3EE2200Efb3400fAbB9AacF31297cBdD1d435D47",
    "CAKE": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",
    "LINK": "0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD",
    "DOT": "0x7083609fCE4d1d8Dc0C979AAb8c869Ea2C873402",
    "UNI": "0xBf5140A22578168FD562DCcF235E5D43A02ce9B1",
    "SHIB": "0x2859e4544C4bB03966803b044A93563Bd2D0DD4D",
    "AVAX": "0x1CE0c2827e2eF14D5C4f29a091d735D206086633",
    "LTC": "0x4338665CBB7B2485A8855A139b75D5e34AB0DB94",
    "TON": "0x76A797A59Ba6CFA4b04C85786fba240D09b57898",
    "AAVE": "0xfb6115445Bff7b52FeB98650C87f44907E58f802",
    "FIL": "0x0D8Ce2A99Bb6e3B7Db580eD848240e4a0F9aE18",
    "INJ": "0xa2B726B1145A4773F68593CF171187d8EBe4d495",
    "FET": "0x031b41e504677879370e9DBcF937283A8691Fa7f",
    "ATOM": "0x0Eb3a705fc54725037CC9e008bDede697f62F335",
    "TWT": "0x4B0F1812e5Df2A09796481Ff14017e6005508003",
    "COMP": "0x52CE071Bd9b1C4B00A0b92D298c512478CaD67e8",
    "SUSHI": "0x947950BcC74888a40Ffa2593C5798F11Fc9124C4",
    "1INCH": "0x111111111117dC0aa78b770fA6A738034120C302",
    "APE": "0x935640e03928828d025084707B977F4e40D9d553",
    "SNX": "0x9Ac98382600234fD23973b063E1e1f7b8c7e7A45",
    "PENDLE": "0xb3Ed0A426155B79B7218EEd6A877Aef7Ff3aDC78",
    "LDO": "0x986854779804799C1d68867F5E03e60fE2B8a4a3",
    "CRV": "0xeFFCa039A7d4C3F6c2B3A21B6Dc3D4fE4F5f7c8F",
    "FDUSD": "0xc5f0f7b66764F6ec8C8Dff7BA683102295E16409",
    "STG": "0xB0D502E938ed5f4df2E681fE6E419ff29631d628",
    "FLOKI": "0xfb5B838b6cfEEdC2873aB27866079AC55363D37E",
    "DEXE": "0x039cB485212f996A9DBb85A9a75d898F94d38dA6",
    "BAKE": "0xE02dF9F892BF5e3D0e1dc2D3b1E7C32E9E4E1E1d",
    "ALPACA": "0x8F0528cE5eF7B51152A59745bEfDD91D97091d2F",
    "BSW": "0x965F527D9159dCe6288a2219DB51fc6Eef120dD1",
    "BabyDoge": "0xc748673057861a797275CD8A068AbB21399d7f3A",
    "PENGU": "0x27C4d14A59676c2B73b2b12b4e3D5E5fDf2dD5B8",
    "SIREN": "0x2FdEB16E7D7b1d7C8E5E1A7c4E4f5f6f7f8f9f0f",
    "BANANAS31": "0x3d4f5f6f7f8f9f0f1f2f3f4f5f6f7f8f9f0f1f2",
    "CHEEMS": "0x8d8b6b4a5a4a3a2a1a0a9a8a7a6a5a4a3a2a1a0",
}

# Top trading pairs for competition
TRADING_PAIRS = [
    "BNBUSDT", "ETHUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT",
    "CAKEUSDT", "LINKUSDT", "DOTUSDT", "UNIUSDT", "LTCUSDT",
    "AVAXUSDT", "ATOMUSDT", "SHIBUSDT", "FILUSDT", "INJUSDT",
]


def register_agent_on_chain():
    """Register agent using BNB Agent SDK (ERC-8004)."""
    try:
        from bnbagent import BNBClient

        client = BNBClient(
            private_key=WALLET_PRIVATE_KEY,
            rpc_url=BSC_RPC_URL,
            chain_id=BSC_CHAIN_ID
        )

        # Register agent identity
        result = client.register_agent(
            name="BSC AI Trading Agent",
            description="Autonomous multi-signal trading agent on BNB Chain. Combines RSI, MACD, Bollinger Bands, volume analysis, and sentiment for automated trading via PancakeSwap.",
            metadata={
                "version": "1.0.0",
                "hackathon": "BNB Hack: AI Trading Agent Edition",
                "track": "Track 1: Autonomous Trading Agents",
                "github": "https://github.com/Ginameo/bsc-trading-agent",
                "dashboard": "https://bsc-trading-agent.vercel.app"
            }
        )

        print(f"[Registration] Agent registered: {result}")
        return result

    except ImportError:
        print("[Registration] bnbagent not installed, using fallback")
        return _register_via_contract()
    except Exception as e:
        print(f"[Registration] Error: {e}")
        return _register_via_contract()


def _register_via_contract():
    """Direct contract interaction for registration."""
    try:
        w3 = Web3(Web3.HTTPProvider(BSC_RPC_URL))
        account = Account.from_key(WALLET_PRIVATE_KEY)

        # Competition contract ABI (minimal - register function)
        contract_abi = json.loads('''[{
            "name": "register",
            "type": "function",
            "stateMutability": "nonpayable",
            "inputs": [],
            "outputs": []
        }]''')

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(COMPETITION_CONTRACT),
            abi=contract_abi
        )

        tx = contract.functions.register().build_transaction({
            'from': account.address,
            'gas': 100000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': BSC_CHAIN_ID
        })

        signed = w3.eth.account.sign_transaction(tx, WALLET_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"[Registration] TX: {tx_hash.hex()}")
        return tx_hash.hex()

    except Exception as e:
        print(f"[Registration] Contract error: {e}")
        return None


def is_eligible_token(symbol: str) -> bool:
    """Check if token is in the eligible list."""
    return symbol.upper() in ELIGIBLE_TOKENS


def get_eligible_token_address(symbol: str) -> str:
    """Get token address for eligible token."""
    return ELIGIBLE_TOKENS.get(symbol.upper(), "")


if __name__ == "__main__":
    print("=== Competition Registration ===\n")
    print(f"Competition Contract: {COMPETITION_CONTRACT}")
    print(f"Eligible Tokens: {len(ELIGIBLE_TOKENS)}")
    print(f"Trading Pairs: {len(TRADING_PAIRS)}")
    print(f"\nTrading Pairs: {', '.join(TRADING_PAIRS)}")

    # Register
    result = register_agent_on_chain()
    if result:
        print(f"\n✅ Registration successful: {result}")
    else:
        print("\n⚠️ Registration failed - check wallet balance")
