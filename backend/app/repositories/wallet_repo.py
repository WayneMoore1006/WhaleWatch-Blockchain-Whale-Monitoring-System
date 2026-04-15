"""
Updated Wallet Repository
"""
from sqlalchemy.orm import Session
from app.models.models import MonitoredWallet
from datetime import datetime


class WalletRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_wallet_by_address(self, address: str):
        return self.db.query(MonitoredWallet).filter_by(address=address).first()

    def get_wallet_by_id(self, wallet_id: int):
        return self.db.query(MonitoredWallet).filter_by(wallet_id=wallet_id).first()

    def get_active_wallets(self):
        return self.db.query(MonitoredWallet).filter_by(is_active=True).all()

    def get_all_wallets(self, chain: str = None):
        q = self.db.query(MonitoredWallet)
        if chain:
            q = q.filter(MonitoredWallet.chain == chain.upper())
        return q.order_by(MonitoredWallet.sort_index.asc(), MonitoredWallet.created_at.desc()).all()

    def get_active_wallets_by_chain(self, chain: str):
        return self.db.query(MonitoredWallet).filter_by(
            is_active=True, chain=chain.upper()).all()

    def create_wallet(self, address: str, chain: str, label: str = None, source: str = "manual"):
        # Build masked address (show first 6 + last 4)
        masked = f"{address[:6]}...{address[-4:]}" if len(address) > 10 else address
        db_wallet = MonitoredWallet(
            address=address,
            masked_address=masked,
            chain=chain.upper(),
            label=label or f"Whale {address[:6]}",
            source=source,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(db_wallet)
        self.db.commit()
        self.db.refresh(db_wallet)
        return db_wallet

    def update_wallet(self, wallet_id: int, **kwargs):
        wallet = self.get_wallet_by_id(wallet_id)
        if not wallet:
            return None
        for k, v in kwargs.items():
            if hasattr(wallet, k):
                setattr(wallet, k, v)
        wallet.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(wallet)
        return wallet

    def bulk_update_sort_index(self, item_orders: list):
        for item in item_orders:
            wallet = self.get_wallet_by_id(item["id"])
            if wallet:
                wallet.sort_index = item["index"]
        self.db.commit()
        return True

    def pause(self, wallet_id: int):
        return self.update_wallet(wallet_id, is_active=False)

    def resume(self, wallet_id: int):
        return self.update_wallet(wallet_id, is_active=True)

    def delete_wallet(self, wallet_id: int) -> bool:
        wallet = self.get_wallet_by_id(wallet_id)
        if not wallet:
            return False
        self.db.delete(wallet)
        self.db.commit()
        return True
