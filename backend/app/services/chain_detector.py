"""
Chain Detector Service
======================
輸入地址字串，判斷屬於 ETH / BSC / SOL。
- Solana base58 (長度 32-44 字元，非 0x 開頭) → SOL
- 0x 開頭 44 字元 → EVM，進一步用 RPC 輕量查詢區分 ETH vs BSC
"""
import os
import re
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Solana base58 charset
_BASE58_RE = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')
_EVM_RE    = re.compile(r'^0x[0-9a-fA-F]{40}$')


def _is_evm(address: str) -> bool:
    return bool(_EVM_RE.match(address))


def _is_solana(address: str) -> bool:
    return (not address.startswith("0x")) and bool(_BASE58_RE.match(address))


def _rpc_get_balance(rpc_url: str, address: str, timeout: int = 5) -> float | None:
    """對 EVM RPC 做 eth_getBalance 輕量查詢。失敗回傳 None。"""
    try:
        resp = requests.post(
            rpc_url,
            json={"jsonrpc": "2.0", "id": 1, "method": "eth_getBalance",
                  "params": [address, "latest"]},
            timeout=timeout
        )
        result = resp.json().get("result")
        if result:
            return int(result, 16) / 1e18
        return 0.0
    except Exception as e:
        logger.warning(f"[chain_detector] RPC balance check failed ({rpc_url[:40]}...): {e}")
        return None


def _rpc_get_nonce(rpc_url: str, address: str, timeout: int = 5) -> int | None:
    """對 EVM RPC 做 eth_getTransactionCount 查詢。失敗回傳 None。"""
    try:
        resp = requests.post(
            rpc_url,
            json={"jsonrpc": "2.0", "id": 1, "method": "eth_getTransactionCount",
                  "params": [address, "latest"]},
            timeout=timeout
        )
        result = resp.json().get("result")
        return int(result, 16) if result else 0
    except Exception as e:
        logger.warning(f"[chain_detector] RPC nonce check failed: {e}")
        return None


def detect_chain(address: str, user_hint: str | None = None) -> dict:
    """
    判斷地址所屬鏈別。

    Returns:
        dict with keys:
          - chain: 'ETH' / 'BSC' / 'SOL' / 'UNKNOWN'
          - ambiguous: True if EVM address active on both ETH + BSC
          - message: 說明字串
    """
    address = address.strip()

    # 使用者明確指定 → 直接信任
    if user_hint and user_hint.upper() in ("ETH", "BSC", "SOL"):
        return {"chain": user_hint.upper(), "ambiguous": False, "message": "User specified"}

    # Solana: base58，非 0x 開頭
    if _is_solana(address):
        return {"chain": "SOL", "ambiguous": False, "message": "Solana base58 address"}

    # EVM: 0x + 40 hex
    if _is_evm(address):
        eth_rpc = os.getenv("ALCHEMY_ETH_RPC", "")
        bsc_rpc = os.getenv("ALCHEMY_BNB_RPC", "")

        # 加入 API key（若 URL 結尾未含 key）
        api_key = os.getenv("ALCHEMY_API_KEY", "")
        if api_key and eth_rpc and not eth_rpc.rstrip("/").endswith(api_key):
            eth_rpc = eth_rpc.rstrip("/") + "/" + api_key
        if api_key and bsc_rpc and not bsc_rpc.rstrip("/").endswith(api_key):
            bsc_rpc = bsc_rpc.rstrip("/") + "/" + api_key

        eth_active, bsc_active = False, False

        # ETH 查詢
        if eth_rpc:
            eth_nonce   = _rpc_get_nonce(eth_rpc, address)
            eth_balance = _rpc_get_balance(eth_rpc, address)
            eth_active  = (eth_nonce is not None and eth_nonce > 0) or \
                          (eth_balance is not None and eth_balance > 0)

        # BSC 查詢
        if bsc_rpc:
            bsc_nonce   = _rpc_get_nonce(bsc_rpc, address)
            bsc_balance = _rpc_get_balance(bsc_rpc, address)
            bsc_active  = (bsc_nonce is not None and bsc_nonce > 0) or \
                          (bsc_balance is not None and bsc_balance > 0)

        if eth_active and bsc_active:
            return {
                "chain": "ETH",   # 預設 ETH，ambiguous=True 讓前端再選
                "ambiguous": True,
                "message": "Address active on both ETH and BSC. Please select chain."
            }
        elif eth_active:
            return {"chain": "ETH", "ambiguous": False, "message": "Active on Ethereum"}
        elif bsc_active:
            return {"chain": "BSC", "ambiguous": False, "message": "Active on BSC"}
        else:
            # 兩邊都沒資料 → 預設 ETH（使用者可手動改）
            return {
                "chain": "ETH",
                "ambiguous": False,
                "message": "No on-chain activity found. Defaulting to ETH."
            }

    return {"chain": "UNKNOWN", "ambiguous": False, "message": "Unrecognized address format"}
