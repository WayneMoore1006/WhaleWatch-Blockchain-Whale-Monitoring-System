"""
Wallet Intelligence Service
============================
接收一個地址，產出完整的分析資料（chain, balance, holdings, txs, counterparties）。
結果從 DB 讀取（wallet_sync 已先同步 Alchemy 資料）。

Performance 策略：
- 若 DB 已有資料 → 立即回傳快取，同步在背景執行（由 router 層用 BackgroundTasks）
- 若 DB 完全沒有 → 同步等待首次 sync（不可避免）
"""
import logging
from datetime import datetime, timedelta
from collections import Counter
from sqlalchemy.orm import Session

from app.models.models import MonitoredWallet, WalletBalance, WalletTokenHolding, WalletTransaction, WalletDailyStat
from app.services.chain_detector import detect_chain
from app.services.wallet_sync import sync_wallet
from app.services.wallet_pnl_service import calculate_pnl

logger = logging.getLogger(__name__)

# 快取 TTL：若上次同步在此時間內，背景 sync 也不重跑
CACHE_TTL_MINUTES = 5


def analyze(address: str, user_chain_hint: str | None, db: Session) -> dict:
    """
    分析指定地址。
    回傳 (result_dict, needs_background_sync: bool)。
    - 若 DB 有資料（即使過期）→ 立即回傳快取，needs_background_sync=True 表示可背景更新
    - 若 DB 完全沒有 → 同步等待首次 sync
    """
    address = address.strip()

    # 1. 取得或建立 wallet record
    wallet = db.query(MonitoredWallet).filter_by(address=address).first()

    if not wallet:
        # 偵測鏈別
        detection = detect_chain(address, user_chain_hint)
        chain = detection["chain"]
        if chain == "UNKNOWN":
            return {"error": "Unrecognized address format", "address": address}, False

        # 建立 wallet 記錄（非 watchlist，只是臨時分析）
        wallet = MonitoredWallet(
            address=address,
            chain=chain,
            is_active=False,  # 非 watchlist，不主動 sync
            source="intelligence_query",
            created_at=datetime.utcnow()
        )
        db.add(wallet)
        try:
            db.commit()
            db.refresh(wallet)
        except Exception as e:
            db.rollback()
            logger.error(f"[wallet_intelligence] Failed to create temp wallet for {address}: {e}")
            return {"error": "DB error", "address": address}, False

    # 2. 判斷是否有任何 DB 快取資料
    has_cached_data = _has_any_data(wallet, db)

    if not has_cached_data:
        # 首次查詢：同步等待 sync（使用者第一次查，必須等）
        logger.info(f"[wallet_intelligence] First-time sync for {address}")
        sync_wallet(wallet, db)
        db.refresh(wallet)
        result = _build_analysis(wallet, db)
        result["sync_status"] = "fresh"
        return result, False

    # 3. 有快取資料 → 立即回傳，判斷是否需要背景更新
    needs_sync = True
    if wallet.last_synced_at:
        elapsed = (datetime.utcnow() - wallet.last_synced_at).total_seconds() / 60
        if elapsed < CACHE_TTL_MINUTES:
            needs_sync = False

    result = _build_analysis(wallet, db)
    result["sync_status"] = "stale" if needs_sync else "fresh"
    return result, needs_sync


def background_sync(address: str, db: Session):
    """由 router 的 BackgroundTasks 呼叫，在回傳 HTTP 後執行 sync。"""
    try:
        wallet = db.query(MonitoredWallet).filter_by(address=address).first()
        if wallet:
            logger.info(f"[wallet_intelligence] Background sync starting for {address}")
            sync_wallet(wallet, db)
            logger.info(f"[wallet_intelligence] Background sync done for {address}")
    except Exception as e:
        logger.error(f"[wallet_intelligence] Background sync failed for {address}: {e}")


def _has_any_data(wallet: MonitoredWallet, db: Session) -> bool:
    """檢查 DB 中是否已有任何資料（只要有 balance 或 tx 就算）。"""
    has_balance = db.query(WalletBalance).filter_by(wallet_id=wallet.wallet_id).first() is not None
    if has_balance:
        return True
    has_tx = db.query(WalletTransaction).filter_by(wallet_id=wallet.wallet_id).first() is not None
    return has_tx


def _build_analysis(wallet: MonitoredWallet, db: Session) -> dict:
    """從 DB 組合完整分析結果。"""
    chain = wallet.chain.upper()

    # Balance
    balance_row = db.query(WalletBalance).filter_by(wallet_id=wallet.wallet_id, chain=chain)\
        .order_by(WalletBalance.snapshot_time.desc()).first()

    balance_info = {}
    if balance_row:
        balance_info = {
            "native_symbol": balance_row.native_symbol,
            "native_balance": float(balance_row.native_balance or 0),
            "native_balance_usd": float(balance_row.native_balance_usd) if balance_row.native_balance_usd else None,
            "total_estimated_usd": float(balance_row.total_estimated_usd) if balance_row.total_estimated_usd else None,
            "price_source": balance_row.price_source,
            "snapshot_time": balance_row.snapshot_time.isoformat() if balance_row.snapshot_time else None
        }
    else:
        balance_info = {"note": "No balance data yet. Sync pending."}

    # Token Holdings
    holdings = db.query(WalletTokenHolding).filter_by(wallet_id=wallet.wallet_id, chain=chain)\
        .order_by(WalletTokenHolding.snapshot_time.desc()).all()

    holdings_list = [
        {
            "token_address": h.token_address,
            "token_symbol": h.token_symbol or "UNK",
            "token_name": h.token_name,
            "amount": float(h.amount or 0),
            "decimals": h.decimals,
            "estimated_usd": float(h.estimated_usd) if h.estimated_usd else None,
            "price_source": h.price_source
        }
        for h in holdings
    ]

    # Recent Transactions
    txs = db.query(WalletTransaction).filter_by(wallet_id=wallet.wallet_id, chain=chain)\
        .order_by(WalletTransaction.tx_time.desc()).limit(50).all()

    tx_list = [
        {
            "tx_hash": t.tx_hash,
            "direction": t.direction,
            "counterparty": t.counterparty,
            "asset_symbol": t.asset_symbol,
            "amount": float(t.amount or 0),
            "amount_usd": float(t.amount_usd) if t.amount_usd else None,
            "tx_type": t.tx_type,
            "tx_time": t.tx_time.isoformat() if t.tx_time else None,
            "block_number": t.block_number
        }
        for t in txs
    ]

    # Counterparties analysis
    counterparty_counts = Counter(
        t.counterparty for t in txs if t.counterparty
    )
    top_counterparties = [
        {"address": addr, "tx_count": count}
        for addr, count in counterparty_counts.most_common(10)
    ]

    # Flow (last 30 days)
    since_30d = datetime.utcnow() - timedelta(days=30)
    in_txs  = [t for t in txs if t.direction == "in" and t.tx_time and t.tx_time >= since_30d]
    out_txs = [t for t in txs if t.direction == "out" and t.tx_time and t.tx_time >= since_30d]

    inflow_usd  = sum(float(t.amount_usd or 0) for t in in_txs)
    outflow_usd = sum(float(t.amount_usd or 0) for t in out_txs)

    # First / Last activity
    oldest_tx = db.query(WalletTransaction).filter_by(wallet_id=wallet.wallet_id)\
        .order_by(WalletTransaction.tx_time.asc()).first()

    # PnL & Win Rate Approximations
    pnl_data = calculate_pnl(txs, holdings)

    # Volume Trend (Chart data) - Daily Stats for last 30 days
    daily_stats = db.query(WalletDailyStat).filter(
        WalletDailyStat.wallet_id == wallet.wallet_id,
        WalletDailyStat.chain == chain,
        WalletDailyStat.stat_date >= (datetime.utcnow() - timedelta(days=30)).date()
    ).order_by(WalletDailyStat.stat_date.asc()).all()

    chart_data = [
        {
            "date": stat.stat_date.isoformat(),
            "tx_count": stat.tx_count,
            "inflow_usd": float(stat.inflow_usd or 0),
            "outflow_usd": float(stat.outflow_usd or 0),
            "netflow_usd": float(stat.netflow_usd or 0)
        }
        for stat in daily_stats
    ]

    return {
        "address": wallet.address,
        "chain": chain,
        "label": wallet.label,
        "is_in_watchlist": wallet.is_active,
        "source": wallet.source,
        "first_active": oldest_tx.tx_time.isoformat() if oldest_tx and oldest_tx.tx_time else None,
        "last_active": wallet.last_activity.isoformat() if wallet.last_activity else None,
        "last_synced_at": wallet.last_synced_at.isoformat() if wallet.last_synced_at else None,
        "balance": balance_info,
        "holdings": holdings_list,
        "recent_transactions": tx_list,
        "top_counterparties": top_counterparties,
        "flow_30d": {
            "inflow_usd": round(inflow_usd, 2),
            "outflow_usd": round(outflow_usd, 2),
            "netflow_usd": round(inflow_usd - outflow_usd, 2)
        },
        "pnl": pnl_data,
        "chart_data": chart_data,
        "risk_signals": _assess_risk(wallet, txs),
        "data_source": "Alchemy RPC → SQL Server"
    }


def _assess_risk(wallet: MonitoredWallet, txs: list) -> dict:
    """簡單風險評估。若資料不足顯示 N/A。"""
    if not txs:
        return {"level": "N/A", "reason": "Insufficient transaction data"}

    recent_24h = [t for t in txs if t.tx_time and t.tx_time >= datetime.utcnow() - timedelta(hours=24)]
    large_txs = [t for t in txs if float(t.amount_usd or 0) > 50_000]

    risk_level = "low"
    reasons = []

    if len(recent_24h) > 20:
        risk_level = "high"
        reasons.append(f"High frequency: {len(recent_24h)} txs in 24h")
    elif len(recent_24h) > 10:
        risk_level = "medium"
        reasons.append(f"Moderate frequency: {len(recent_24h)} txs in 24h")

    if large_txs:
        risk_level = max(risk_level, "medium", key=lambda x: ["low", "medium", "high"].index(x))
        reasons.append(f"{len(large_txs)} large transfers (>$50k) found")

    return {
        "level": risk_level,
        "reason": "; ".join(reasons) if reasons else "Normal activity pattern"
    }
