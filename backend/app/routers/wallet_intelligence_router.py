"""
Wallet Intelligence Router
===========================
POST /api/wallet-intelligence/analyze
GET  /api/wallet-intelligence/{address}
GET  /api/wallet-intelligence/{address}/transactions
GET  /api/wallet-intelligence/{address}/holdings

Performance 策略：
- /analyze 若 DB 有快取資料，立即回傳快取，並用 BackgroundTasks 在 HTTP 回應後才觸發 sync
- 首次查詢（DB 無資料）才同步等待 sync
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db, SessionLocal
from app.services import wallet_intelligence
from app.models.models import MonitoredWallet, WalletTransaction, WalletTokenHolding

router = APIRouter(prefix="/api/wallet-intelligence", tags=["Wallet Intelligence"])


class AnalyzeRequest(BaseModel):
    address: str
    chain: Optional[str] = None   # 若指定則跳過 chain detection


def _run_background_sync(address: str):
    """BackgroundTasks callback — 使用獨立 DB session，在 HTTP 回應後執行。"""
    db = SessionLocal()
    try:
        wallet_intelligence.background_sync(address, db)
    finally:
        db.close()


@router.post("/analyze")
async def analyze_wallet(
    req: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    分析地址。
    - 若 DB 已有快取資料：立即回傳快取，背景更新（使用者無需等候 sync）
    - 若 DB 完全沒有資料：同步等待首次 sync（不可避免）
    """
    result, needs_background_sync = wallet_intelligence.analyze(req.address, req.chain, db)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # 若資料過期，在 HTTP 回傳後才觸發背景 sync
    if needs_background_sync:
        background_tasks.add_task(_run_background_sync, req.address)

    return result


@router.get("/{address}")
async def get_wallet_summary(address: str, db: Session = Depends(get_db)):
    """取得已存在 DB 中的地址分析摘要（輕量版，不重新同步）。"""
    wallet = db.query(MonitoredWallet).filter_by(address=address).first()
    if not wallet:
        return {
            "address": address,
            "message": "No on-chain data yet. Use POST /analyze to trigger analysis.",
            "data_available": False
        }

    from app.models.models import WalletBalance
    bal = db.query(WalletBalance).filter_by(wallet_id=wallet.wallet_id, chain=wallet.chain)\
        .order_by(WalletBalance.snapshot_time.desc()).first()

    return {
        "address": wallet.address,
        "chain": wallet.chain,
        "label": wallet.label,
        "is_in_watchlist": wallet.is_active,
        "last_synced_at": wallet.last_synced_at.isoformat() if wallet.last_synced_at else None,
        "native_balance": float(bal.native_balance or 0) if bal else None,
        "native_balance_usd": float(bal.native_balance_usd) if bal and bal.native_balance_usd else None,
        "total_estimated_usd": float(bal.total_estimated_usd) if bal and bal.total_estimated_usd else None,
        "data_available": True
    }


@router.get("/{address}/transactions")
async def get_wallet_transactions(address: str,
                                  limit: int = Query(50, ge=1, le=200),
                                  direction: Optional[str] = None,
                                  db: Session = Depends(get_db)):
    """取得地址交易紀錄（來自 DB）。"""
    wallet = db.query(MonitoredWallet).filter_by(address=address).first()
    if not wallet:
        return {"address": address, "transactions": [], "message": "No data. Use /analyze first."}

    q = db.query(WalletTransaction).filter_by(wallet_id=wallet.wallet_id)\
        .order_by(WalletTransaction.tx_time.desc())
    if direction:
        q = q.filter(WalletTransaction.direction == direction.lower())

    txs = q.limit(limit).all()
    return {
        "address": address,
        "chain": wallet.chain,
        "transactions": [
            {
                "tx_hash": t.tx_hash,
                "direction": t.direction,
                "counterparty": t.counterparty,
                "asset_symbol": t.asset_symbol,
                "amount": float(t.amount or 0),
                "amount_usd": float(t.amount_usd) if t.amount_usd else None,
                "tx_time": t.tx_time.isoformat() if t.tx_time else None,
                "tx_type": t.tx_type,
                "block_number": t.block_number
            }
            for t in txs
        ]
    }


@router.get("/{address}/holdings")
async def get_wallet_holdings(address: str, db: Session = Depends(get_db)):
    """取得地址 token holdings（來自 DB）。"""
    wallet = db.query(MonitoredWallet).filter_by(address=address).first()
    if not wallet:
        return {"address": address, "holdings": [], "message": "No data. Use /analyze first."}

    holdings = db.query(WalletTokenHolding).filter_by(wallet_id=wallet.wallet_id, chain=wallet.chain)\
        .order_by(WalletTokenHolding.snapshot_time.desc()).all()

    return {
        "address": wallet.address,
        "chain": wallet.chain,
        "holdings": [
            {
                "token_address": h.token_address,
                "token_symbol": h.token_symbol,
                "token_name": h.token_name,
                "amount": float(h.amount or 0),
                "estimated_usd": float(h.estimated_usd) if h.estimated_usd else None,
                "price_source": h.price_source
            }
            for h in holdings
        ]
    }
