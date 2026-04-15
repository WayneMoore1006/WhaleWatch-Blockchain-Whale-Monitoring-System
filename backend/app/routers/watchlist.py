"""
Watchlist Router
================
CRUD + pause / resume / refresh operations on monitored wallets.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.repositories.wallet_repo import WalletRepository
from app.services.chain_detector import detect_chain
from app.services.wallet_sync import sync_wallet
from app.models.models import MonitoredWallet, WalletBalance, Alert
from sqlalchemy import func

router = APIRouter(prefix="/api/watchlist", tags=["Watchlist"])


class AddWalletRequest(BaseModel):
    address: str
    chain: Optional[str] = None   # 若未指定，自動偵測
    label: Optional[str] = None


from typing import List

class UpdateWalletRequest(BaseModel):
    label: Optional[str] = None
    is_active: Optional[bool] = None

class ReorderItem(BaseModel):
    id: int
    index: int

class ReorderRequest(BaseModel):
    orders: List[ReorderItem]


def _wallet_to_dict(wallet: MonitoredWallet, bal_map: dict, alert_map: dict) -> dict:
    """將 MonitoredWallet ORM 物件轉為 API 回傳 dict（使用預先批次查詢的 maps）。"""
    bal = bal_map.get(wallet.wallet_id)
    alert_count = alert_map.get(wallet.wallet_id, 0)

    return {
        "id": wallet.wallet_id,
        "address": wallet.address,
        "masked_address": wallet.masked_address or f"{wallet.address[:6]}...{wallet.address[-4:]}",
        "chain": wallet.chain,
        "label": wallet.label,
        "is_active": wallet.is_active,
        "source": wallet.source,
        "created_at": wallet.created_at.isoformat() if wallet.created_at else None,
        "last_synced_at": wallet.last_synced_at.isoformat() if wallet.last_synced_at else None,
        "last_activity": wallet.last_activity.isoformat() if wallet.last_activity else None,
        "native_balance": float(bal.native_balance or 0) if bal else None,
        "native_balance_usd": float(bal.native_balance_usd) if bal and bal.native_balance_usd else None,
        "native_symbol": bal.native_symbol if bal else None,
        "alert_count": alert_count
    }


def _build_batch_maps(wallet_ids: list, db: Session) -> tuple[dict, dict]:
    """批次查詢 balance 和 alert count，回傳 (bal_map, alert_map)。"""
    # 1. 每個 wallet 的最新 balance（用 subquery 取最大 snapshot_time）
    bal_map = {}
    if wallet_ids:
        from sqlalchemy.orm import aliased
        # 取每個 wallet 的最新一筆 balance
        latest_bals = db.query(WalletBalance).filter(
            WalletBalance.wallet_id.in_(wallet_ids)
        ).order_by(WalletBalance.wallet_id, WalletBalance.snapshot_time.desc()).all()
        # 只取每個 wallet_id 的第一筆（最新）
        for bal in latest_bals:
            if bal.wallet_id not in bal_map:
                bal_map[bal.wallet_id] = bal

    # 2. 每個 wallet 的 new alert count
    alert_map = {}
    if wallet_ids:
        rows = db.query(
            Alert.wallet_id, func.count(Alert.alert_id)
        ).filter(
            Alert.wallet_id.in_(wallet_ids),
            Alert.status == "new"
        ).group_by(Alert.wallet_id).all()
        alert_map = {wid: cnt for wid, cnt in rows}

    return bal_map, alert_map


@router.get("")
async def get_watchlist(chain: Optional[str] = None, db: Session = Depends(get_db)):
    """取得 Watchlist 地址清單（批次查詢，無 N+1）"""
    repo = WalletRepository(db)
    wallets = repo.get_all_wallets(chain=chain)
    wallet_ids = [w.wallet_id for w in wallets]
    bal_map, alert_map = _build_batch_maps(wallet_ids, db)
    return [_wallet_to_dict(w, bal_map, alert_map) for w in wallets]


@router.post("")
async def add_wallet(req: AddWalletRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """新增 Wallet 到 Watchlist，自動偵測鏈別，背景觸發初始同步。"""
    address = req.address.strip()
    if not address:
        raise HTTPException(status_code=400, detail="Address is required")

    repo = WalletRepository(db)

    # 檢查是否重複
    existing = repo.get_wallet_by_address(address)
    if existing:
        raise HTTPException(status_code=409, detail="Address already in watchlist")

    # Chain detection
    detection = detect_chain(address, req.chain)
    chain = detection["chain"]

    if chain == "UNKNOWN":
        raise HTTPException(status_code=400, detail="Cannot recognize address format.")

    # 建立 wallet
    wallet = repo.create_wallet(
        address=address,
        chain=chain,
        label=req.label,
        source="manual"
    )

    # 背景觸發初始同步（不阻塞 response）
    from app.core.database import SessionLocal
    def _bg_sync(wid: int):
        s = SessionLocal()
        try:
            w = s.query(MonitoredWallet).filter_by(wallet_id=wid).first()
            if w: sync_wallet(w, s)
        except Exception:
            pass
        finally:
            s.close()
    background_tasks.add_task(_bg_sync, wallet.wallet_id)

    bm, am = _build_batch_maps([wallet.wallet_id], db)
    return {
        "message": "Wallet added successfully — syncing in background",
        "wallet": _wallet_to_dict(wallet, bm, am),
        "chain_detection": detection
    }


@router.patch("/{wallet_id}")
async def update_wallet(wallet_id: int, req: UpdateWalletRequest, db: Session = Depends(get_db)):
    """更新 wallet 標籤或狀態。"""
    repo = WalletRepository(db)
    updates = {k: v for k, v in req.dict().items() if v is not None}
    wallet = repo.update_wallet(wallet_id, **updates)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    bm, am = _build_batch_maps([wallet.wallet_id], db)
    return _wallet_to_dict(wallet, bm, am)


@router.delete("/{wallet_id}")
async def delete_wallet(wallet_id: int, db: Session = Depends(get_db)):
    """刪除 wallet 及其所有相關資料。"""
    repo = WalletRepository(db)
    success = repo.delete_wallet(wallet_id)
    if not success:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return {"message": "Wallet deleted successfully", "id": wallet_id}


@router.post("/{wallet_id}/refresh")
async def refresh_wallet(wallet_id: int, db: Session = Depends(get_db)):
    """手動觸發 wallet 同步。"""
    repo = WalletRepository(db)
    wallet = repo.get_wallet_by_id(wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    result = sync_wallet(wallet, db)
    bm, am = _build_batch_maps([wallet.wallet_id], db)
    return {
        "message": "Sync completed" if result.get("success") else "Sync failed",
        "result": result,
        "wallet": _wallet_to_dict(wallet, bm, am)
    }


@router.post("/{wallet_id}/pause")
async def pause_wallet(wallet_id: int, db: Session = Depends(get_db)):
    """暫停監控。"""
    repo = WalletRepository(db)
    wallet = repo.pause(wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    bm, am = _build_batch_maps([wallet.wallet_id], db)
    return {"message": "Monitoring paused", "wallet": _wallet_to_dict(wallet, bm, am)}


@router.post("/{wallet_id}/resume")
async def resume_wallet(wallet_id: int, db: Session = Depends(get_db)):
    """恢復監控。"""
    repo = WalletRepository(db)
    wallet = repo.resume(wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    bm, am = _build_batch_maps([wallet.wallet_id], db)
    return {"message": "Monitoring resumed", "wallet": _wallet_to_dict(wallet, bm, am)}

@router.put("/reorder")
async def reorder_wallets(req: ReorderRequest, db: Session = Depends(get_db)):
    """重新排序 Watchlist。"""
    repo = WalletRepository(db)
    items = [{"id": item.id, "index": item.index} for item in req.orders]
    repo.bulk_update_sort_index(items)
    return {"message": "Order updated successfully"}
