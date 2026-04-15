"""
Alert Engine Service
====================
掃描所有 active watchlist 地址，依 8 條規則產生 alerts 寫入 DB。
每次執行只產生新警報（避免重複）。
"""
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import MonitoredWallet, WalletTransaction, WalletBalance, Alert

logger = logging.getLogger(__name__)

# ── 觸發門檻設定 ──────────────────────────────────────────────
THRESHOLDS = {
    "LARGE_TRANSFER_IN_USD":   {"ETH": 50_000, "BSC": 20_000, "SOL": 10_000},
    "LARGE_TRANSFER_OUT_USD":  {"ETH": 50_000, "BSC": 20_000, "SOL": 10_000},
    "HIGH_FREQUENCY_TX_DAY":   15,   # 單日超過 N 筆
    "BALANCE_CHANGE_PCT":      20.0, # 餘額變動超過 20%
    "RAPID_TRANSFERS_WINDOW":  60,   # 分鐘
    "RAPID_TRANSFERS_COUNT":   5,    # 60 分鐘內超過 5 筆
    "DORMANT_DAYS":            30,   # 超過 30 天未動視為休眠
}


def _alert_exists(wallet_id: int, alert_type: str, since_hours: int, db: Session) -> bool:
    """避免短時間內重複觸發相同警報。"""
    since = datetime.utcnow() - timedelta(hours=since_hours)
    return db.query(Alert).filter(
        Alert.wallet_id == wallet_id,
        Alert.alert_type == alert_type,
        Alert.created_at >= since
    ).first() is not None


def _create_alert(wallet: MonitoredWallet, alert_type: str, severity: str,
                  title: str, description: str, tx_hash: str | None, db: Session):
    """寫入一筆警報。"""
    alert = Alert(
        wallet_id=wallet.wallet_id,
        chain=wallet.chain,
        alert_type=alert_type,
        severity=severity,
        title=title,
        description=description,
        source="watchlist",
        status="new",
        related_tx_hash=tx_hash,
        created_at=datetime.utcnow()
    )
    db.add(alert)
    logger.info(f"[alert_engine] {alert_type} ({severity}) → {wallet.address[:10]}...")


def _check_large_transfers(wallet: MonitoredWallet, db: Session):
    """大額轉入 / 轉出。"""
    chain = wallet.chain.upper()
    threshold = THRESHOLDS["LARGE_TRANSFER_IN_USD"].get(chain, 50_000)
    since = datetime.utcnow() - timedelta(hours=1)  # 只看最近 1 小時的新 tx

    recent_txs = db.query(WalletTransaction).filter(
        WalletTransaction.wallet_id == wallet.wallet_id,
        WalletTransaction.tx_time >= since,
        WalletTransaction.amount_usd >= Decimal(str(threshold))
    ).all()

    for tx in recent_txs:
        atype = "LARGE_TRANSFER_IN" if tx.direction == "in" else "LARGE_TRANSFER_OUT"
        if _alert_exists(wallet.wallet_id, atype, since_hours=2, db=db):
            continue
        amt_usd = float(tx.amount_usd or 0)
        direction_text = "received" if tx.direction == "in" else "sent"
        _create_alert(
            wallet, atype,
            severity="high",
            title=f"Large Transfer {tx.direction.upper()} — ${amt_usd:,.0f}",
            description=f"Address {wallet.address[:12]}... {direction_text} {float(tx.amount):.4f} {tx.asset_symbol} (≈${amt_usd:,.0f}) tx: {tx.tx_hash[:16]}...",
            tx_hash=tx.tx_hash,
            db=db
        )


def _check_high_frequency(wallet: MonitoredWallet, db: Session):
    """單日交易次數異常增加。"""
    from datetime import date
    today = date.today()
    tx_count = db.query(func.count(WalletTransaction.id)).filter(
        WalletTransaction.wallet_id == wallet.wallet_id,
        func.cast(WalletTransaction.tx_time, db.bind.dialect.name == "mssql" and "date" or "date") == today
    ).scalar() or 0

    # 避免 SQL Server / SQLite 相容問題，改用 timedelta
    since_today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tx_count = db.query(func.count(WalletTransaction.id)).filter(
        WalletTransaction.wallet_id == wallet.wallet_id,
        WalletTransaction.tx_time >= since_today
    ).scalar() or 0

    threshold = THRESHOLDS["HIGH_FREQUENCY_TX_DAY"]
    if tx_count >= threshold and not _alert_exists(wallet.wallet_id, "HIGH_FREQUENCY", since_hours=6, db=db):
        _create_alert(
            wallet, "HIGH_FREQUENCY",
            severity="medium",
            title=f"High Frequency Trading — {tx_count} txs today",
            description=f"Address {wallet.address[:12]}... has made {tx_count} transactions today, exceeding the threshold of {threshold}.",
            tx_hash=None,
            db=db
        )


def _check_rapid_transfers(wallet: MonitoredWallet, db: Session):
    """短時間內多筆轉帳。"""
    window = timedelta(minutes=THRESHOLDS["RAPID_TRANSFERS_WINDOW"])
    count_threshold = THRESHOLDS["RAPID_TRANSFERS_COUNT"]
    since = datetime.utcnow() - window

    count = db.query(func.count(WalletTransaction.id)).filter(
        WalletTransaction.wallet_id == wallet.wallet_id,
        WalletTransaction.tx_time >= since
    ).scalar() or 0

    if count >= count_threshold and not _alert_exists(wallet.wallet_id, "RAPID_TRANSFERS", since_hours=2, db=db):
        _create_alert(
            wallet, "RAPID_TRANSFERS",
            severity="medium",
            title=f"Rapid Transfers — {count} txs in {THRESHOLDS['RAPID_TRANSFERS_WINDOW']}min",
            description=f"Address {wallet.address[:12]}... sent {count} transactions within {THRESHOLDS['RAPID_TRANSFERS_WINDOW']} minutes.",
            tx_hash=None,
            db=db
        )


def _check_dormant_wallet(wallet: MonitoredWallet, db: Session):
    """長時間未動後重新活躍。"""
    if not wallet.last_activity:
        return
    dormant_days = THRESHOLDS["DORMANT_DAYS"]
    dormant_threshold = datetime.utcnow() - timedelta(days=dormant_days)

    # 取最新交易時間
    latest_tx = db.query(WalletTransaction).filter_by(wallet_id=wallet.wallet_id)\
        .order_by(WalletTransaction.tx_time.desc()).first()
    if not latest_tx or not latest_tx.tx_time:
        return

    # 取前一筆交易時間（第二新）
    prev_tx = db.query(WalletTransaction).filter_by(wallet_id=wallet.wallet_id)\
        .order_by(WalletTransaction.tx_time.desc()).offset(1).first()

    if prev_tx and prev_tx.tx_time and prev_tx.tx_time < dormant_threshold:
        if not _alert_exists(wallet.wallet_id, "DORMANT_WALLET_ACTIVE", since_hours=24, db=db):
            idle_days = (latest_tx.tx_time - prev_tx.tx_time).days
            _create_alert(
                wallet, "DORMANT_WALLET_ACTIVE",
                severity="medium",
                title=f"Dormant Wallet Active — {idle_days} days idle",
                description=f"Address {wallet.address[:12]}... was inactive for {idle_days} days and just made a new transaction.",
                tx_hash=latest_tx.tx_hash,
                db=db
            )


def run(db: Session) -> int:
    """
    優化版 Alert Engine：
    1. 批次拉取所有 active wallets。
    2. 批次預載最近 24h 的 Alerts (防止重複觸發快取)。
    3. 批次預載最近 30 天的交易數據，分組處理。
    4. 記憶體中判斷規則，最後批次寫入。
    """
    # 1. 取得所有活躍錢包
    wallets = db.query(MonitoredWallet).filter_by(is_active=True).all()
    if not wallets: return 0
    wids = [w.wallet_id for w in wallets]
    wallet_map = {w.wallet_id: w for w in wallets}

    # 2. 預載既有警報 (過去 24h)，用於去重判定
    since_24h = datetime.utcnow() - timedelta(hours=24)
    existing_alerts = db.query(Alert.wallet_id, Alert.alert_type).filter(
        Alert.wallet_id.in_(wids),
        Alert.created_at >= since_24h
    ).all()
    # 快取格式: {(wid, atype): True}
    alert_cache = {(a.wallet_id, a.alert_type): True for a in existing_alerts}

    # 3. 預載交易數據 (最近 30 天，用於大部分規則)
    since_30d = datetime.utcnow() - timedelta(days=30)
    # 為了效能，我們只取必要的欄位
    tx_rows = db.query(WalletTransaction).filter(
        WalletTransaction.wallet_id.in_(wids),
        WalletTransaction.tx_time >= since_30d
    ).order_by(WalletTransaction.wallet_id, WalletTransaction.tx_time.desc()).all()

    # 依錢包分組
    txs_by_wallet: dict[int, list[WalletTransaction]] = {wid: [] for wid in wids}
    for tx in tx_rows:
        txs_by_wallet[tx.wallet_id].append(tx)

    # 4. 準備產生新警報
    new_alert_objs = []
    
    # 時間點快照
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    one_hour_ago = now - timedelta(hours=1)
    rapid_window = now - timedelta(minutes=THRESHOLDS["RAPID_TRANSFERS_WINDOW"])
    dormant_delta = timedelta(days=THRESHOLDS["DORMANT_DAYS"])

    for wid, wallet_txs in txs_by_wallet.items():
        wallet = wallet_map[wid]
        
        # ── 規則 A: Large Transfers (最近 1 小時) ──
        threshold = THRESHOLDS["LARGE_TRANSFER_IN_USD"].get(wallet.chain.upper(), 50_000)
        recent_large_txs = [t for t in wallet_txs if t.tx_time >= one_hour_ago and t.amount_usd >= Decimal(str(threshold))]
        for tx in recent_large_txs:
            atype = "LARGE_TRANSFER_IN" if tx.direction == "in" else "LARGE_TRANSFER_OUT"
            if (wid, atype) not in alert_cache:
                amt_usd = float(tx.amount_usd or 0)
                new_alert_objs.append(Alert(
                    wallet_id=wid, chain=wallet.chain, alert_type=atype, severity="high",
                    title=f"Large Transfer {tx.direction.upper()} — ${amt_usd:,.0f}",
                    description=f"Address {wallet.address[:12]}... {'received' if tx.direction == 'in' else 'sent'} {float(tx.amount):.4f} {tx.asset_symbol} (≈${amt_usd:,.0f})",
                    source="watchlist", status="new", related_tx_hash=tx.tx_hash, created_at=now
                ))
                alert_cache[(wid, atype)] = True # 避免同一次 run 重複

        # ── 規則 B: High Frequency (今日) ──
        today_txs = [t for t in wallet_txs if t.tx_time >= today_start]
        if len(today_txs) >= THRESHOLDS["HIGH_FREQUENCY_TX_DAY"]:
            if (wid, "HIGH_FREQUENCY") not in alert_cache:
                new_alert_objs.append(Alert(
                    wallet_id=wid, chain=wallet.chain, alert_type="HIGH_FREQUENCY", severity="medium",
                    title=f"High Frequency Trading — {len(today_txs)} txs today",
                    description=f"Address {wallet.address[:12]}... has made {len(today_txs)} transactions today.",
                    source="watchlist", status="new", created_at=now
                ))
                alert_cache[(wid, "HIGH_FREQUENCY")] = True

        # ── 規則 C: Rapid Transfers ──
        rapid_txs = [t for t in wallet_txs if t.tx_time >= rapid_window]
        if len(rapid_txs) >= THRESHOLDS["RAPID_TRANSFERS_COUNT"]:
            if (wid, "RAPID_TRANSFERS") not in alert_cache:
                new_alert_objs.append(Alert(
                    wallet_id=wid, chain=wallet.chain, alert_type="RAPID_TRANSFERS", severity="medium",
                    title=f"Rapid Transfers — {len(rapid_txs)} txs in {THRESHOLDS['RAPID_TRANSFERS_WINDOW']}min",
                    description=f"Address {wallet.address[:12]}... sent {len(rapid_txs)} transactions within {THRESHOLDS['RAPID_TRANSFERS_WINDOW']} minutes.",
                    source="watchlist", status="new", created_at=now
                ))
                alert_cache[(wid, "RAPID_TRANSFERS")] = True

        # ── 規則 D: Dormant Wallet Active ──
        if len(wallet_txs) >= 2:
            latest_tx = wallet_txs[0]
            prev_tx = wallet_txs[1]
            if latest_tx.tx_time and prev_tx.tx_time:
                if (latest_tx.tx_time - prev_tx.tx_time) >= dormant_delta:
                    if (wid, "DORMANT_WALLET_ACTIVE") not in alert_cache:
                        idle_days = (latest_tx.tx_time - prev_tx.tx_time).days
                        new_alert_objs.append(Alert(
                            wallet_id=wid, chain=wallet.chain, alert_type="DORMANT_WALLET_ACTIVE", severity="medium",
                            title=f"Dormant Wallet Active — {idle_days} days idle",
                            description=f"Address {wallet.address[:12]}... was inactive for {idle_days} days and just made a new transaction.",
                            source="watchlist", status="new", related_tx_hash=latest_tx.tx_hash, created_at=now
                        ))
                        alert_cache[(wid, "DORMANT_WALLET_ACTIVE")] = True

    # 5. 批次寫入資料庫
    if new_alert_objs:
        try:
            db.bulk_save_objects(new_alert_objs)
            db.commit()
            logger.info(f"[alert_engine] Optimized Run: Batch inserted {len(new_alert_objs)} alerts.")
        except Exception as e:
            db.rollback()
            logger.error(f"[alert_engine] Batch commit failed: {e}")
            return 0
    else:
        logger.info("[alert_engine] Optimized Run: No new alerts generated.")

    return len(new_alert_objs)
