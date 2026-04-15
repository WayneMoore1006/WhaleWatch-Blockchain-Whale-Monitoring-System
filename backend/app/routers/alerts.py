"""
Alerts Router
=============
GET   /api/alerts
PATCH /api/alerts/{id}/read
PATCH /api/alerts/{id}/archive
POST  /api/alerts/rebuild
POST  /api/external-alerts/sync
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.repositories.alert_repo import AlertRepository
from app.services import alert_engine, external_alert_ingestor
from app.models.models import MonitoredWallet

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])
external_router = APIRouter(prefix="/api/external-alerts", tags=["External Alerts"])


def _alert_to_dict(alert, wallet_addr_map: dict) -> dict:
    return {
        "id": alert.alert_id,
        "alert_type": alert.alert_type,
        "chain": alert.chain,
        "wallet_address": wallet_addr_map.get(alert.wallet_id),
        "wallet_id": alert.wallet_id,
        "severity": alert.severity,
        "title": alert.title,
        "description": alert.description,
        "source": alert.source,
        "status": alert.status,
        "related_tx_hash": alert.related_tx_hash,
        "created_at": alert.created_at.isoformat() if alert.created_at else None
    }


@router.get("")
async def get_alerts(
    chain: Optional[str] = None,
    severity: Optional[str] = None,
    source: Optional[str] = None,
    alert_type: Optional[str] = None,
    watchlist_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """取得警報清單，支援多條件篩選。批次查 wallet address 避免 N+1。"""
    repo = AlertRepository(db)
    src = "watchlist" if watchlist_only else source
    alerts = repo.get_alerts(
        limit=limit, chain=chain, severity=severity,
        source=src, alert_type=alert_type
    )

    # 批次取 wallet addresses（一次 DB 查詢取代 N 次）
    wallet_ids = list({a.wallet_id for a in alerts if a.wallet_id})
    wallet_addr_map: dict[int, str] = {}
    if wallet_ids:
        rows = db.query(MonitoredWallet.wallet_id, MonitoredWallet.address)\
            .filter(MonitoredWallet.wallet_id.in_(wallet_ids)).all()
        wallet_addr_map = {wid: addr for wid, addr in rows}

    return [_alert_to_dict(a, wallet_addr_map) for a in alerts]


@router.patch("/{alert_id}/read")
async def mark_read(alert_id: int, db: Session = Depends(get_db)):
    """標記警報為已讀。"""
    repo = AlertRepository(db)
    alert = repo.mark_read(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    addr_map = {}
    if alert.wallet_id:
        w = db.query(MonitoredWallet).filter_by(wallet_id=alert.wallet_id).first()
        if w: addr_map[alert.wallet_id] = w.address
    return {"message": "Marked as read", "alert": _alert_to_dict(alert, addr_map)}


@router.patch("/{alert_id}/archive")
async def archive_alert(alert_id: int, db: Session = Depends(get_db)):
    """封存警報。"""
    repo = AlertRepository(db)
    alert = repo.mark_archived(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    addr_map = {}
    if alert.wallet_id:
        w = db.query(MonitoredWallet).filter_by(wallet_id=alert.wallet_id).first()
        if w: addr_map[alert.wallet_id] = w.address
    return {"message": "Alert archived", "alert": _alert_to_dict(alert, addr_map)}


@router.post("/rebuild")
async def rebuild_alerts(db: Session = Depends(get_db)):
    """手動觸發 alert engine 重新掃描所有 watchlist wallets。"""
    count = alert_engine.run(db)
    return {"message": "Alert engine completed", "new_alerts_generated": count}


@external_router.post("/sync")
async def sync_external_alerts(db: Session = Depends(get_db)):
    """手動觸發外部來源警報擷取。"""
    count = external_alert_ingestor.run(db)
    return {"message": "External alerts synced", "new_alerts": count}
