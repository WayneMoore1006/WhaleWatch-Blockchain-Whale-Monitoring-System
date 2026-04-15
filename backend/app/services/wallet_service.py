from app.integrations.blockchain_client import BlockchainClient
from app.repositories.wallet_repo import WalletRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.alert_repo import AlertRepository
from app.models.models import MonitoredWallet
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import decimal

class WalletService:
    def __init__(self, db: Optional[Session] = None):
        self.client = BlockchainClient()
        self.db = db
        if db:
            self.wallet_repo = WalletRepository(db)
            self.tx_repo = TransactionRepository(db)
            self.alert_repo = AlertRepository(db)
        else:
            self.wallet_repo = None
            self.tx_repo = None
            self.alert_repo = None

    def sync_wallet_data(self, address: str, chain: str = "eth"):
        """
        Fetch fresh data from Alchemy and sync to DB.
        """
        if not self.db:
            return None

        # 1. Fetch data from Alchemy
        try:
            balance_data = self.client.get_wallet_balance(address, chain)
            tx_list = self.client.get_wallet_transactions(address, chain, limit=20)
            
            is_solana = chain.lower() == "sol"
            divisor = 10**9 if is_solana else 10**18
            
            balance_normalized = 0
            if balance_data and "balance" in balance_data:
                balance_normalized = float(balance_data["balance"]) / divisor

            # 2. Get or Create Wallet in DB
            wallet = self.wallet_repo.get_wallet_by_address(address)
            if not wallet:
                # Map chain string to ID
                chain_id = 1 if chain.lower() == "eth" else 2 # Default to BSC/BNB for now if not eth
                wallet = self.wallet_repo.create_wallet(address, chain_id=chain_id, label="New Whale")
            
            # 3. Update balance
            wallet.last_balance = decimal.Decimal(str(balance_normalized))
            
            # 4. Save/Update Transactions and Check for Alerts
            for tx in tx_list:
                # Save transaction
                self.tx_repo.save_transaction(wallet.wallet_id, tx)
                
                # Real-time Alert Logic: > 1 ETH/BNB/SOL
                val = float(tx.get("value", 0))
                if val > 1.0: 
                    self.alert_repo.create_alert(
                        wallet_id=wallet.wallet_id,
                        type="Large Transaction",
                        message=f"Large transfer detected: {val:.2f} {chain.upper()} by {wallet.label or address[:8]}",
                        severity="high"
                    )
            
            self.db.commit()
            return wallet
        except Exception as e:
            print(f"Error syncing wallet {address}: {e}")
            self.db.rollback()
            return None

    def get_wallet_intelligence(self, address: str, chain: str = "eth"):
        """
        Returns the deep dive view.
        """
        self.sync_wallet_data(address, chain)
        
        wallet = self.wallet_repo.get_wallet_by_address(address)
        txs = self.tx_repo.get_transactions_by_wallet(wallet.wallet_id) if wallet else []
        
        return {
            "address": address,
            "chain": chain,
            "label": wallet.label if wallet else "Unknown",
            "native_balance": float(wallet.last_balance) if wallet else 0,
            "recent_transactions": [
                {
                    "hash": tx.tx_hash,
                    "value": float(tx.value),
                    "from_address": tx.from_address,
                    "to_address": tx.to_address,
                    "timestamp": tx.block_timestamp.isoformat() if tx.block_timestamp else None
                } for tx in txs[:10]
            ],
            "data_source": "Alchemy"
        }

    def get_watchlist_data(self, chain_id: int = None):
        """
        Returns all wallets in the DB.
        """
        if not self.db:
            return []
            
        query = self.db.query(MonitoredWallet)
        if chain_id:
            query = query.filter(MonitoredWallet.chain_id == chain_id)
        wallets = query.all()
        
        results = []
        for w in wallets:
            results.append({
                "address": w.address,
                "balance": float(w.last_balance) if w.last_balance else 0,
                "status": "Active" if w.is_active else "Inactive",
                "label": w.label or "Whale",
                "chain_id": w.chain_id
            })
        return results
