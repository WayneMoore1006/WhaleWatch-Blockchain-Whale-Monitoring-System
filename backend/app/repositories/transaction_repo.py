from sqlalchemy.orm import Session
from app.models.models import Transaction, TokenTransfer
from app.repositories.base_repo import BaseRepository
from datetime import datetime

class TransactionRepository(BaseRepository):
    def save_transaction(self, wallet_id: int, tx_data: dict):
        tx = Transaction(
            tx_hash=tx_data.get("hash") or tx_data.get("tx_hash"),
            wallet_id=wallet_id,
            from_address=tx_data.get("fromAddress") or tx_data.get("from"),
            to_address=tx_data.get("toAddress") or tx_data.get("to"),
            value=tx_data.get("value"),
            block_number=tx_data.get("blockNum"),
            block_timestamp=datetime.utcnow(), # Fallback
            method_name=tx_data.get("category")
        )
        self.db.add(tx)
        try:
            self.db.commit()
            return tx
        except:
            self.db.rollback()
            return None

    def get_recent_transactions(self, wallet_id: int, limit: int = 10):
        return self.db.query(Transaction).filter(Transaction.wallet_id == wallet_id).order_by(Transaction.tx_id.desc()).limit(limit).all()
