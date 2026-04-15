import os
from dotenv import load_dotenv
from app.integrations.providers.alchemy_evm import AlchemyEVMProvider
from app.integrations.providers.alchemy_solana import AlchemySolanaProvider

load_dotenv()

class BlockchainClient:
    def __init__(self):
        self.providers = {}
        self.api_key = os.getenv("ALCHEMY_API_KEY")
        
        # Initialize providers for different chains
        self._init_providers()

    def _init_providers(self):
        # EVM Chains
        evm_chains = {
            "eth": os.getenv("ALCHEMY_ETH_RPC", "https://eth-mainnet.g.alchemy.com/v2/"),
            "bnb": os.getenv("ALCHEMY_BNB_RPC", "https://bnb-mainnet.g.alchemy.com/v2/"),
            "base": os.getenv("ALCHEMY_BASE_RPC", "https://base-mainnet.g.alchemy.com/v2/"),
            "polygon": os.getenv("ALCHEMY_POLYGON_RPC", "https://polygon-mainnet.g.alchemy.com/v2/"),
            "arbitrum": os.getenv("ALCHEMY_ARBITRUM_RPC", "https://arb-mainnet.g.alchemy.com/v2/"),
        }
        
        for name, url in evm_chains.items():
            self.providers[name] = AlchemyEVMProvider(url)
            
        # Solana
        sol_rpc = os.getenv("ALCHEMY_SOL_RPC", "https://solana-mainnet.g.alchemy.com/v2/")
        self.providers["sol"] = AlchemySolanaProvider(sol_rpc)

    def get_provider(self, chain: str):
        chain = chain.lower()
        if chain not in self.providers:
            # Default to ETH if chain not found, or raise error
            return self.providers.get("eth")
        return self.providers[chain]

    def get_wallet_balance(self, address: str, chain: str = "eth"):
        provider = self.get_provider(chain)
        return provider.get_balance(address)

    def get_wallet_transactions(self, address: str, chain: str = "eth", limit: int = 10):
        provider = self.get_provider(chain)
        return provider.get_transactions(address, limit)

    def get_token_balances(self, address: str, chain: str = "eth"):
        provider = self.get_provider(chain)
        return provider.get_token_balances(address)
