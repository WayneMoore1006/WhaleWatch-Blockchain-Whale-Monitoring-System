from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.alert_repo import AlertRepository
from app.services.dashboard_service import DashboardService
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])
wallets_router = APIRouter(prefix="/api/wallets", tags=["Wallets"])
alerts_router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

# --- Dashboard Endpoints ---

@router.get("/metrics")
async def get_dashboard_metrics(db: Session = Depends(get_db)):
    service = DashboardService(db)
    return service.get_dashboard_stats()

@alerts_router.get("/")
async def get_alerts(db: Session = Depends(get_db)):
    repo = AlertRepository(db)
    alerts = repo.get_alerts(limit=50)
    return [
        {
            "id": a.alert_id,
            "wallet_id": a.wallet_id,
            "type": a.alert_type,
            "severity": a.severity.capitalize(),
            "description": a.message,
            "timestamp": a.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "status": a.status
        } for a in alerts
    ]

@router.get("/volume-chart")
async def get_volume_chart(db: Session = Depends(get_db)):
    service = DashboardService(db)
    return service._get_volume_trend()

# --- Wallet Endpoints ---

@wallets_router.get("/watchlist")
async def get_watchlist(chain_id: Optional[int] = None, db: Session = Depends(get_db)):
    service = WalletService(db)
    return service.get_watchlist_data(chain_id)

@wallets_router.get("/intelligence/{address}")
async def get_intelligence(address: str, chain: str = "eth", db: Session = Depends(get_db)):
    service = WalletService(db)
    data = service.get_wallet_intelligence(address, chain)
    if not data:
        raise HTTPException(status_code=404, detail="Wallet not found or sync failed")
    return data

@wallets_router.post("/sync/{address}")
async def sync_wallet(address: str, chain: str = "eth", db: Session = Depends(get_db)):
    service = WalletService(db)
    wallet = service.sync_wallet_data(address, chain)
    return {"message": "Sync completed", "address": address}

# --- Alert Endpoints ---

@alerts_router.get("/recent")
async def get_recent_alerts(limit: int = 10, db: Session = Depends(get_db)):
    from app.repositories.alert_repo import AlertRepository
    repo = AlertRepository(db)
    alerts = repo.get_alerts(limit=limit)
    return [
        {
            "id": a.alert_id,
            "type": a.alert_type,
            "message": a.message,
            "severity": a.severity,
            "timestamp": a.created_at.isoformat() if a.created_at else None,
            "isRead": a.status == "read"
        } for a in alerts
    ]
