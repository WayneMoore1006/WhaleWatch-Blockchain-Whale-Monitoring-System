import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.integrations.providers.base_provider import BaseProvider

class AlchemyEVMProvider(BaseProvider):
    def __init__(self, chain_rpc_url: str):
        self.rpc_url = chain_rpc_url
        self.api_key = os.getenv("ALCHEMY_API_KEY")
        # Ensure the API key is appended if not already in the URL
        if self.api_key and self.api_key not in self.rpc_url:
            self.rpc_url = self.rpc_url.rstrip('/') + '/' + self.api_key

    def get_balance(self, address: str):
        result = self._make_rpc_call(self.rpc_url, "eth_getBalance", [address, "latest"])
        if "result" in result:
            return {"balance": str(int(result["result"], 16))}
        return None

    def get_token_balances(self, address: str):
        # Use Alchemy Enhanced API
        result = self._make_rpc_call(self.rpc_url, "alchemy_getTokenBalances", [address])
        tokens = []
        if "result" in result and "tokenBalances" in result["result"]:
            for item in result["result"]["tokenBalances"]:
                # We would normally fetch metadata here if needed
                tokens.append({
                    "token_address": item["contractAddress"],
                    "balance": str(int(item["tokenBalance"], 16)) if item["tokenBalance"] != "0x" else "0"
                })
        return tokens

    def get_token_metadata(self, contract_address: str):
        result = self._make_rpc_call(self.rpc_url, "alchemy_getTokenMetadata", [contract_address])
        if "result" in result:
            return result["result"]
        return None

    def get_transactions(self, address: str, limit: int = 10):
        # Use Alchemy Asset Transfers API — 並行取 out + in 兩個方向
        params_out = {
            "fromBlock": "0x0",
            "toBlock": "latest",
            "fromAddress": address,
            "category": ["external", "internal", "erc20", "erc721", "erc1155"],
            "maxCount": "0x190" # 400 records
        }
        params_in = {
            "fromBlock": "0x0",
            "toBlock": "latest",
            "toAddress": address,
            "category": ["external", "internal", "erc20", "erc721", "erc1155"],
            "maxCount": "0x190" # 400 records
        }

        transfers = []
        # 並行送出兩個 RPC 請求，縮短約一半等待時間
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(self._make_rpc_call, self.rpc_url, "alchemy_getAssetTransfers", [params_out]): "out",
                executor.submit(self._make_rpc_call, self.rpc_url, "alchemy_getAssetTransfers", [params_in]): "in",
            }
            for future in as_completed(futures):
                try:
                    res = future.result()
                    transfers.extend(res.get("result", {}).get("transfers", []))
                except Exception:
                    pass  # 單方向失敗不影響另一方向

        # 依 blockNum 降冪排序，取最近 limit 筆
        transfers.sort(key=lambda x: int(x.get("blockNum", "0x0"), 16), reverse=True)
        return transfers[:limit]
