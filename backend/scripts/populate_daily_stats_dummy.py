import sys
import os
import random
from datetime import date, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.models import MonitoredWallet, WalletDailyStat

def seed_daily_stats():
    db = SessionLocal()
    try:
        wallets = db.query(MonitoredWallet).all()
        if not wallets:
            print("No wallets found. Add some to the watchlist first.")
            return

        today = date.today()
        # Create 7 days of mock stats for each wallet
        for wallet in wallets:
            # Check if stats already exist
            existing = db.query(WalletDailyStat).filter_by(wallet_id=wallet.wallet_id).count()
            if existing > 0:
                print(f"Stats already exist for wallet {wallet.address}, skipping...")
                continue
            
            for i in range(7, -1, -1):
                stat_date = today - timedelta(days=i)
                tx_count = random.randint(1, 15)
                
                # Mock realistic data depending on chain
                if wallet.chain.upper() == 'ETH':
                    inflow = random.uniform(1000, 50000)
                    outflow = random.uniform(1000, 50000)
                elif wallet.chain.upper() == 'BSC':
                    inflow = random.uniform(100, 20000)
                    outflow = random.uniform(100, 20000)
                else:
                    inflow = random.uniform(500, 30000)
                    outflow = random.uniform(500, 30000)
                    
                netflow = inflow - outflow
                
                stat = WalletDailyStat(
                    wallet_id=wallet.wallet_id,
                    chain=wallet.chain,
                    stat_date=stat_date,
                    tx_count=tx_count,
                    inflow_usd=inflow,
                    outflow_usd=outflow,
                    netflow_usd=netflow,
                    active_counterparties=random.randint(1, 5)
                )
                db.add(stat)
                
        db.commit()
        print("Successfully seeded daily stats for all wallets!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_daily_stats()
