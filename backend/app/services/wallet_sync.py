"""
Wallet Sync Service
====================
針對單一 wallet 從 Alchemy RPC 同步：
  1. native balance
  2. token holdings (只限 EVM alchemy_getTokenBalances)
  3. 近期交易（最近 100 筆）
同步完後更新 last_synced_at，並計算 wallet_daily_stats。
"""
import json
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from app.integrations.blockchain_client import BlockchainClient
from app.models.models import (
    MonitoredWallet, WalletBalance, WalletTokenHolding,
    WalletTransaction, WalletDailyStat
)
from app.services.pricing import get_native_price, estimate_usd
from app.services.wallet_classification_service import classify_transaction

logger = logging.getLogger(__name__)

# 大額轉帳門檻（USD）—— 超過此值會觸發 alert engine 注意
LARGE_TRANSFER_THRESHOLD_USD = 10_000


def _get_chain_symbol(chain: str) -> str:
    return {"ETH": "ETH", "BSC": "BNB", "SOL": "SOL"}.get(chain.upper(), chain.upper())


def _get_alchemy_chain_key(chain: str) -> str:
    """BlockchainClient 使用的 key"""
    return {"ETH": "eth", "BSC": "bnb", "SOL": "sol"}.get(chain.upper(), "eth")


from concurrent.futures import ThreadPoolExecutor

def sync_wallet(wallet: MonitoredWallet, db: Session) -> dict:
    """
    Main sync entry point.
    並行優化：Native Balance, Tokens, Txs 同時抓取。
    """
    chain = wallet.chain.upper()
    chain_key = _get_alchemy_chain_key(chain)
    address = wallet.address
    result = {"success": False, "balance_usd": None, "tx_count": 0}

    client = BlockchainClient()
    provider = client.get_provider(chain_key)

    try:
        # ── 並行抓取階段 ───────────────────────────────────────────
        # 使用 ThreadPoolExecutor 並行執行 3 個外部請求
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_bal = executor.submit(provider.get_balance, address)
            future_tokens = executor.submit(provider.get_token_balances, address) if chain in ("ETH", "BSC") else None
            future_txs = executor.submit(provider.get_transactions, address, limit=100)

            # 等待所有結果
            balance_raw = future_bal.result()
            tokens_raw = future_tokens.result() if future_tokens else []
            txs_raw = future_txs.result()

        # ── 串行寫入階段 (Session 安全) ──────────────────────────────
        
        # 1. Native Balance 處理
        native_symbol = _get_chain_symbol(chain)
        is_sol = chain == "SOL"
        divisor = 10**9 if is_sol else 10**18

        native_amount = 0.0
        if balance_raw and "balance" in balance_raw:
            native_amount = float(balance_raw["balance"]) / divisor

        native_price = get_native_price(chain)
        native_usd = round(native_amount * native_price, 2) if native_price else None

        # 寫入 wallet_balances
        db.query(WalletBalance).filter_by(wallet_id=wallet.wallet_id, chain=chain).delete()
        db_balance = WalletBalance(
            wallet_id=wallet.wallet_id,
            chain=chain,
            native_symbol=native_symbol,
            native_balance=Decimal(str(native_amount)),
            native_balance_usd=Decimal(str(native_usd)) if native_usd else None,
            total_estimated_usd=Decimal(str(native_usd)) if native_usd else None,
            price_source="coingecko" if native_price else None,
            snapshot_time=datetime.utcnow()
        )
        db.add(db_balance)
        result["balance_usd"] = native_usd

        # 2. Token Holdings 處理
        if tokens_raw:
            _process_token_holdings(wallet, tokens_raw, chain, native_usd, db)

        # 3. Transactions 處理
        tx_count = _process_transactions(wallet, txs_raw, chain, address, db)
        result["tx_count"] = tx_count

        # 4. Daily Stats 重建
        _rebuild_daily_stats(wallet, chain, db)

        # 5. 更新時間戳
        wallet.last_synced_at = datetime.utcnow()
        wallet.updated_at = datetime.utcnow()
        db.commit()
        
        result["success"] = True
        logger.info(f"[wallet_sync] Parallel Synced {address} ({chain}): bal={native_amount}, txs={tx_count}")

    except Exception as e:
        db.rollback()
        logger.error(f"[wallet_sync] Failed to sync {address}: {e}", exc_info=True)
        result["error"] = str(e)

    return result

# ── 下方為重構出的處理函式 (只負責邏輯與寫入，不發起 RPC) ─────────────

def _process_token_holdings(wallet: MonitoredWallet, tokens_raw: list, chain: str, native_usd: Optional[float], db: Session):
    """處理抓取到的 token 資料並寫入 DB。"""
    try:
        from app.integrations.blockchain_client import BlockchainClient
        client = BlockchainClient()
        chain_key = _get_alchemy_chain_key(chain)
        provider = client.get_provider(chain_key)

        db.query(WalletTokenHolding).filter_by(wallet_id=wallet.wallet_id, chain=chain).delete()
        total_token_usd = 0.0
        
        # 內層並行獲取 Metadata 與價格 (優化版)
        metadata_and_price_results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            for token in tokens_raw:
                token_addr = token.get("token_address")
                if not token_addr: continue
                
                # 並行提交任務：1. 獲取 Metadata, 2. 獲取價格估算
                metadata_future = executor.submit(provider.get_token_metadata, token_addr)
                
                metadata_and_price_results.append({
                    "token_addr": token_addr,
                    "balance_raw": token.get("balance", "0"),
                    "metadata_future": metadata_future
                })
            
            for item in metadata_and_price_results:
                token_addr = item["token_addr"]
                balance_raw = item["balance_raw"]
                
                # 等待 Metadata 结果
                meta = item["metadata_future"].result() or {}
                symbol = meta.get("symbol") or "UNK"
                name = meta.get("name") or symbol
                # 若 symbol 含有 "?" 或异常字符，可能是 RPC 回傳問題或編碼問題，但在 Python 中通常是正常的
                
                decimals = int(meta.get("decimals") or 18)
                amount = int(balance_raw) / (10 ** decimals)
                
                # 取得價格 (優先用 address)
                token_usd, price_src = estimate_usd(amount, symbol, chain, address=token_addr)
                
                if token_usd:
                    total_token_usd += token_usd

                db.add(WalletTokenHolding(
                    wallet_id=wallet.wallet_id,
                    chain=chain,
                    token_address=token_addr,
                    token_symbol=symbol,
                    token_name=name,
                    amount=Decimal(str(amount)),
                    decimals=decimals,
                    estimated_usd=Decimal(str(token_usd)) if token_usd else None,
                    price_source=price_src,
                    snapshot_time=datetime.utcnow()
                ))

        # 更新大額餘額估值
        latest_bal = db.query(WalletBalance).filter_by(wallet_id=wallet.wallet_id, chain=chain).first()
        if latest_bal:
            nv = float(latest_bal.native_balance_usd or 0)
            latest_bal.total_estimated_usd = Decimal(str(round(nv + total_token_usd, 2)))

    except Exception as e:
        logger.warning(f"[wallet_sync] Token processing failed: {e}")

def _process_transactions(wallet: MonitoredWallet, txs_raw: list, chain: str, address: str, db: Session) -> int:
    """處理抓取到的交易資料並寫入 DB。"""
    count = 0
    try:
        for tx in txs_raw:
            tx_hash = tx.get("hash") or tx.get("signature", "")
            if not tx_hash: continue

            existing = db.query(WalletTransaction).filter_by(wallet_id=wallet.wallet_id, tx_hash=tx_hash).first()
            if existing: continue

            from_addr = (tx.get("from") or tx.get("from_address") or "").lower()
            direction = "out" if from_addr == address.lower() else "in"
            counterparty = (tx.get("to") or tx.get("to_address") or "").lower() if direction == "out" else from_addr

            raw_value = tx.get("value") or tx.get("amount") or 0
            amount = float(raw_value)
            asset_symbol = tx.get("asset") or _get_chain_symbol(chain)
            amount_usd, _ = estimate_usd(amount, asset_symbol, chain)

            ts = tx.get("metadata", {}).get("blockTimestamp") or tx.get("block_timestamp") or tx.get("blockTime")
            tx_time = None
            if ts:
                try:
                    # 處理 ISO 格式或 Unix Timestamp (秒)
                    if isinstance(ts, str):
                        tx_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    else:
                        tx_time = datetime.utcfromtimestamp(int(ts))
                except Exception: pass

            db.add(WalletTransaction(
                wallet_id=wallet.wallet_id,
                chain=chain,
                tx_hash=tx_hash,
                direction=direction,
                counterparty=counterparty or None,
                asset_symbol=asset_symbol,
                amount=Decimal(str(amount)),
                amount_usd=Decimal(str(amount_usd)) if amount_usd else None,
                tx_type=classify_transaction(tx, address),
                block_number=tx.get("blockNum") or tx.get("block_number"),
                tx_time=tx_time,
                raw_payload_json=json.dumps(tx, default=str)[:4000],
                created_at=datetime.utcnow()
            ))
            count += 1

        latest_tx = db.query(WalletTransaction).filter_by(wallet_id=wallet.wallet_id).order_by(WalletTransaction.tx_time.desc()).first()
        if latest_tx and latest_tx.tx_time:
            wallet.last_activity = latest_tx.tx_time
    except Exception as e:
        logger.warning(f"[wallet_sync] Transaction processing failed: {e}")
    return count



def _rebuild_daily_stats(wallet: MonitoredWallet, chain: str, db: Session):
    """從 wallet_transactions 重算最近 30 天的 wallet_daily_stats。"""
    try:
        since = datetime.utcnow() - timedelta(days=30)
        txs = db.query(WalletTransaction).filter(
            WalletTransaction.wallet_id == wallet.wallet_id,
            WalletTransaction.chain == chain,
            WalletTransaction.tx_time >= since
        ).all()

        # 依日期分組
        daily: dict[date, dict] = {}
        for tx in txs:
            if not tx.tx_time:
                continue
            d = tx.tx_time.date()
            if d not in daily:
                daily[d] = {"tx_count": 0, "inflow": 0.0, "outflow": 0.0, "counterparties": set()}
            daily[d]["tx_count"] += 1
            usd = float(tx.amount_usd or 0)
            if tx.direction == "in":
                daily[d]["inflow"] += usd
            else:
                daily[d]["outflow"] += usd
            if tx.counterparty:
                daily[d]["counterparties"].add(tx.counterparty)

        for stat_date, stats in daily.items():
            existing = db.query(WalletDailyStat).filter_by(
                wallet_id=wallet.wallet_id, chain=chain, stat_date=stat_date).first()
            netflow = stats["inflow"] - stats["outflow"]
            if existing:
                existing.tx_count = stats["tx_count"]
                existing.inflow_usd = Decimal(str(round(stats["inflow"], 2)))
                existing.outflow_usd = Decimal(str(round(stats["outflow"], 2)))
                existing.netflow_usd = Decimal(str(round(netflow, 2)))
                existing.active_counterparties = len(stats["counterparties"])
            else:
                db.add(WalletDailyStat(
                    wallet_id=wallet.wallet_id,
                    chain=chain,
                    stat_date=stat_date,
                    tx_count=stats["tx_count"],
                    inflow_usd=Decimal(str(round(stats["inflow"], 2))),
                    outflow_usd=Decimal(str(round(stats["outflow"], 2))),
                    netflow_usd=Decimal(str(round(netflow, 2))),
                    active_counterparties=len(stats["counterparties"])
                ))
    except Exception as e:
        logger.warning(f"[wallet_sync] Daily stats rebuild failed: {e}")
