"""
Dashboard Aggregation Service
==============================
從 DB 計算 Dashboard 各個 panel 的資料。
所有計算都在此 service 完成，不在前端計算。
"""
import logging
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import (
    MonitoredWallet, WalletTransaction, WalletDailyStat,
    WalletBalance, Alert
)

logger = logging.getLogger(__name__)

LARGE_TRANSFER_USD_ETH = 50_000    # ETH 鏈大額門檻
LARGE_TRANSFER_USD_BSC = 20_000    # BSC 鏈大額門檻
LARGE_TRANSFER_USD_SOL = 10_000    # SOL 鏈大額門檻


def _large_tx_threshold(chain: str) -> float:
    return {"ETH": LARGE_TRANSFER_USD_ETH, "BSC": LARGE_TRANSFER_USD_BSC, "SOL": LARGE_TRANSFER_USD_SOL}.get(chain.upper(), LARGE_TRANSFER_USD_ETH)


def get_overview(chain: str, db: Session) -> dict:
    """
    取得指定鏈的概覽資料。
    包含：tracked_wallets, tx_24h, inflow_usd, outflow_usd, netflow_usd, active_alerts
    """
    chain = chain.upper()
    since_24h = datetime.utcnow() - timedelta(hours=24)
    today = date.today()

    try:
        # 追蹤錢包數
        tracked = db.query(func.count(MonitoredWallet.wallet_id)).filter(
            MonitoredWallet.chain == chain,
            MonitoredWallet.is_active == True
        ).scalar() or 0

        # 24h 交易數
        tx_24h = db.query(func.count(WalletTransaction.id)).join(
            MonitoredWallet, WalletTransaction.wallet_id == MonitoredWallet.wallet_id
        ).filter(
            WalletTransaction.chain == chain,
            WalletTransaction.tx_time >= since_24h
        ).scalar() or 0

        # 今日 Net Flow（從 daily_stats）
        daily_agg = db.query(
            func.sum(WalletDailyStat.inflow_usd).label("inflow"),
            func.sum(WalletDailyStat.outflow_usd).label("outflow"),
            func.sum(WalletDailyStat.netflow_usd).label("netflow")
        ).join(
            MonitoredWallet, WalletDailyStat.wallet_id == MonitoredWallet.wallet_id
        ).filter(
            WalletDailyStat.chain == chain,
            WalletDailyStat.stat_date == today
        ).first()

        inflow = float(daily_agg.inflow or 0)
        outflow = float(daily_agg.outflow or 0)
        netflow = float(daily_agg.netflow or 0)

        # 活躍警報數
        active_alerts = db.query(func.count(Alert.alert_id)).filter(
            Alert.chain == chain,
            Alert.status == "new"
        ).scalar() or 0

        return {
            "chain": chain,
            "tracked_wallets": tracked,
            "tx_24h": tx_24h,
            "inflow_usd": round(inflow, 2),
            "outflow_usd": round(outflow, 2),
            "netflow_usd": round(netflow, 2),
            "active_alerts": active_alerts,
            "synced_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"[dashboard] get_overview({chain}) error: {e}", exc_info=True)
        return {"chain": chain, "error": str(e), "synced_at": datetime.utcnow().isoformat()}


def get_top_wallets(chain: str, limit: int, db: Session) -> list:
    """
    取得最活躍的 wallet 清單（依近 24h tx 數排序）。
    """
    chain = chain.upper()
    since_24h = datetime.utcnow() - timedelta(hours=24)

    try:
        rows = db.query(
            MonitoredWallet.wallet_id,
            MonitoredWallet.address,
            MonitoredWallet.label,
            MonitoredWallet.chain,
            MonitoredWallet.last_synced_at,
            func.count(WalletTransaction.id).label("tx_count"),
            func.sum(WalletTransaction.amount_usd).label("volume_usd")
        ).outerjoin(
            WalletTransaction,
            (WalletTransaction.wallet_id == MonitoredWallet.wallet_id) &
            (WalletTransaction.tx_time >= since_24h)
        ).filter(
            MonitoredWallet.chain == chain,
            MonitoredWallet.is_active == True
        ).group_by(
            MonitoredWallet.wallet_id,
            MonitoredWallet.address,
            MonitoredWallet.label,
            MonitoredWallet.chain,
            MonitoredWallet.last_synced_at
        ).order_by(func.count(WalletTransaction.id).desc()).limit(limit).all()

        result = []
        # 批次取最新餘額，避免 N+1
        wids = [row.wallet_id for row in rows]
        bal_map: dict[int, float] = {}
        if wids:
            bals = db.query(WalletBalance).filter(
                WalletBalance.wallet_id.in_(wids), WalletBalance.chain == chain
            ).order_by(WalletBalance.wallet_id, WalletBalance.snapshot_time.desc()).all()
            for b in bals:
                if b.wallet_id not in bal_map:
                    bal_map[b.wallet_id] = round(float(b.native_balance_usd or 0), 2)

        for row in rows:
            result.append({
                "address": row.address,
                "label": row.label or "Whale",
                "chain": row.chain,
                "tx_count_24h": row.tx_count or 0,
                "volume_usd_24h": round(float(row.volume_usd or 0), 2),
                "native_balance_usd": bal_map.get(row.wallet_id),
                "last_synced_at": row.last_synced_at.isoformat() if row.last_synced_at else None
            })
        return result

    except Exception as e:
        logger.error(f"[dashboard] get_top_wallets({chain}) error: {e}", exc_info=True)
        return []


def get_recent_transfers(chain: str, limit: int, db: Session) -> list:
    """
    取得大額轉帳記錄。JOIN 帶出 wallet address，避免 N+1。
    """
    chain = chain.upper()
    threshold = _large_tx_threshold(chain)

    try:
        rows = db.query(
            WalletTransaction, MonitoredWallet.address
        ).join(
            MonitoredWallet, WalletTransaction.wallet_id == MonitoredWallet.wallet_id
        ).filter(
            WalletTransaction.chain == chain,
            WalletTransaction.amount_usd >= threshold
        ).order_by(WalletTransaction.tx_time.desc()).limit(limit).all()

        return [
            {
                "tx_hash": tx.tx_hash,
                "chain": tx.chain,
                "direction": tx.direction,
                "counterparty": tx.counterparty,
                "asset_symbol": tx.asset_symbol,
                "amount": float(tx.amount or 0),
                "amount_usd": float(tx.amount_usd or 0),
                "tx_time": tx.tx_time.isoformat() if tx.tx_time else None,
                "wallet_address": wallet_addr
            }
            for tx, wallet_addr in rows
        ]

    except Exception as e:
        logger.error(f"[dashboard] get_recent_transfers({chain}) error: {e}", exc_info=True)
        return []


def get_tx_volume_trend(chain: str, days: int, db: Session) -> list:
    """
    取得每日 TX 量趨勢（過去 N 天）。
    資料來自 wallet_daily_stats。
    """
    chain = chain.upper()
    since = date.today() - timedelta(days=days)

    try:
        rows = db.query(
            WalletDailyStat.stat_date,
            func.sum(WalletDailyStat.tx_count).label("tx_count"),
            func.sum(WalletDailyStat.inflow_usd).label("inflow_usd"),
            func.sum(WalletDailyStat.outflow_usd).label("outflow_usd"),
            func.sum(WalletDailyStat.netflow_usd).label("netflow_usd")
        ).join(
            MonitoredWallet, WalletDailyStat.wallet_id == MonitoredWallet.wallet_id
        ).filter(
            WalletDailyStat.chain == chain,
            WalletDailyStat.stat_date >= since
        ).group_by(WalletDailyStat.stat_date).order_by(WalletDailyStat.stat_date).all()

        return [
            {
                "date": str(r.stat_date),
                "tx_count": r.tx_count or 0,
                "inflow_usd": round(float(r.inflow_usd or 0), 2),
                "outflow_usd": round(float(r.outflow_usd or 0), 2),
                "netflow_usd": round(float(r.netflow_usd or 0), 2)
            }
            for r in rows
        ]

    except Exception as e:
        logger.error(f"[dashboard] get_tx_volume_trend({chain}) error: {e}", exc_info=True)
        return []
