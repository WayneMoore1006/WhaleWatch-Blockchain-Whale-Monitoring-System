import os
from app.integrations.providers.base_provider import BaseProvider

class AlchemySolanaProvider(BaseProvider):
    def __init__(self, rpc_url: str):
        self.rpc_url = rpc_url
        self.api_key = os.getenv("ALCHEMY_API_KEY")
        if self.api_key and self.api_key not in self.rpc_url:
            self.rpc_url = self.rpc_url.rstrip('/') + '/' + self.api_key

    def get_balance(self, address: str):
        result = self._make_rpc_call(self.rpc_url, "getBalance", [address])
        if "result" in result:
            return {"balance": str(result["result"]["value"])}
        return None

    def get_token_balances(self, address: str):
        # Solana SPL tokens
        params = [
            address,
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}, # Token Program
            {"encoding": "jsonParsed"}
        ]
        result = self._make_rpc_call(self.rpc_url, "getTokenAccountsByOwner", params)
        tokens = []
        if "result" in result and "value" in result["result"]:
            for item in result["result"]["value"]:
                info = item["account"]["data"]["parsed"]["info"]
                tokens.append({
                    "token_address": info["mint"],
                    "balance": info["tokenAmount"]["amount"]
                })
        return tokens

    def get_transactions(self, address: str, limit: int = 10):
        # 1. 先抓 signatures (最近的交易列表)
        sig_result = self._make_rpc_call(self.rpc_url, "getSignaturesForAddress", [address, {"limit": limit}])
        signatures = sig_result.get("result", [])
        
        # 2. 為每一筆 signature 抓詳細內容以解析 amount 和 counterparty
        # 注意：Solana 詳情請求較重，這裡我們只抓最近的幾筆
        detailed_txs = []
        for sig_info in signatures:
            sig = sig_info.get("signature")
            if not sig: continue
            
            # 抓詳細資料
            params = [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
            tx_res = self._make_rpc_call(self.rpc_url, "getTransaction", params)
            tx_data = tx_res.get("result")
            
            if tx_data:
                # 簡單結構化：嘗試從訊息中找到 signer 和第一個接收者
                # 這裡是一個簡化的解析，實務上 Solana 複雜得多
                meta = tx_data.get("meta", {})
                tx_msg = tx_data.get("transaction", {}).get("message", {})
                
                # 提取基本欄位以補足 WalletTransaction 所需
                tx_obj = {
                    "hash": sig,
                    "block_number": tx_data.get("slot"),
                    "block_timestamp": sig_info.get("blockTime"),
                    "from": "", 
                    "to": "",
                    "value": 0,
                    "asset": "SOL",
                    "raw_solana_meta": sig_info # 保留原始 signature 資訊（含 blockTime）
                }
                
                # 從 accountKeys 找 signer (通常是 index 0)
                accounts = tx_msg.get("accountKeys", [])
                if accounts:
                    signer = accounts[0]
                    if isinstance(signer, dict): # jsonParsed format
                        tx_obj["from"] = signer.get("pubkey")
                    else:
                        tx_obj["from"] = signer
                
                # 估計金額：從 postBalances vs preBalances 差額 (Lamports)
                # 這是對原生 SOL 的粗估
                pre = meta.get("preBalances", [])
                post = meta.get("postBalances", [])
                if len(pre) > 0 and len(post) > 0:
                    diff = abs(post[0] - pre[0])
                    tx_obj["value"] = diff / (10**9) # SOL
                
                detailed_txs.append(tx_obj)
            else:
                # Fallback: 若抓不到詳情，至少保留 signature 資訊
                detailed_txs.append({
                    "hash": sig,
                    "block_number": sig_info.get("slot"),
                    "block_timestamp": sig_info.get("blockTime"),
                    "asset": "SOL"
                })
                
        return detailed_txs
