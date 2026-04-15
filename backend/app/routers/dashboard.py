"""
Dashboard Router
================
GET /api/dashboard/overview
GET /api/dashboard/top-wallets
GET /api/dashboard/recent-transfers
GET /api/dashboard/tx-volume-trend
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services import dashboard_aggregation

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/overview")
async def get_overview(chain: str = Query("ETH", description="Chain: ETH / BSC / SOL"),
                       db: Session = Depends(get_db)):
    """Dashboard 概覽：追蹤錢包數、24h 交易數、淨流量、警報數"""
    return dashboard_aggregation.get_overview(chain, db)


@router.get("/top-wallets")
async def get_top_wallets(chain: str = Query("ETH"),
                          limit: int = Query(10, ge=1, le=50),
                          db: Session = Depends(get_db)):
    """最活躍 wallets（依近 24h 交易數排序）"""
    return dashboard_aggregation.get_top_wallets(chain, limit, db)


@router.get("/recent-transfers")
async def get_recent_transfers(chain: str = Query("ETH"),
                               limit: int = Query(20, ge=1, le=100),
                               db: Session = Depends(get_db)):
    """大額轉帳記錄"""
    return dashboard_aggregation.get_recent_transfers(chain, limit, db)


@router.get("/tx-volume-trend")
async def get_tx_volume_trend(chain: str = Query("ETH"),
                              days: int = Query(7, ge=1, le=30),
                              db: Session = Depends(get_db)):
    """每日 TX 量趨勢（來自 wallet_daily_stats）"""
    data = dashboard_aggregation.get_tx_volume_trend(chain, days, db)
    if not data:
        return {"chain": chain, "trend": [], "message": "Data sync pending — no daily stats yet"}
    return {"chain": chain, "trend": data}
