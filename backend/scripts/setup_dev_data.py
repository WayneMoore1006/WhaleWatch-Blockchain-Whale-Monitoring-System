
import sys
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine
from app.models.models import Chain, MonitoredWallet, Base
from app.services.wallet_sync import sync_wallet

load_dotenv()

def get_dynamic_addresses(rpc_url: str, count: int = 5):
    """從區塊鏈動態抓取最近活躍的地址，避免寫死敏感數據。"""
    if not rpc_url or "your_alchemy_api_key_here" in rpc_url:
        return []
        
    addresses = set()
    try:
        # 1. 取得最新區塊
        resp = requests.post(rpc_url, json={
            "jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1
        }, timeout=10)
        res = resp.json().get("result")
        if not res: return []
        
        block_num = int(res, 16)
        
        # 2. 往前找直到湊滿地址
        while len(addresses) < count and block_num > 0:
            resp = requests.post(rpc_url, json={
                "jsonrpc": "2.0", 
                "method": "eth_getBlockByNumber", 
                "params": [hex(block_num), True], 
                "id": 1
            }, timeout=10)
            
            block_data = resp.json().get("result", {})
            for tx in block_data.get("transactions", []):
                if tx.get("to"): addresses.add(tx["to"])
                if len(addresses) >= count: break
            block_num -= 1
            
        return list(addresses)
    except Exception as e:
        print(f"Error fetching dynamic addresses: {e}")
        return []

def setup():
    print("=== Whale Watching Platform Setup (Safe Mode) ===")
    
    # 1. 初始化資料表結構
    print("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 2. 初始化鏈資料 (Chains)
        chains_to_seed = [
            {"name": "Ethereum", "symbol": "ETH", "rpc_env": "ALCHEMY_ETH_RPC"},
            {"name": "BNB Chain", "symbol": "BSC", "rpc_env": "ALCHEMY_BNB_RPC"},
        ]
        
        for c in chains_to_seed:
            chain_obj = db.query(Chain).filter(Chain.symbol == c["symbol"]).first()
            if not chain_obj:
                print(f"Adding chain: {c['name']}")
                chain_obj = Chain(name=c["name"], symbol=c["symbol"], is_active=True)
                db.add(chain_obj)
                db.commit()
                db.refresh(chain_obj)
            
            # 3. 動態抓取測試錢包 (不寫死地址)
            rpc = os.getenv(c["rpc_env"])
            # 若為 .env.example 預設值，嘗試讀取 ALCHEMY_API_KEY 補充
            api_key = os.getenv("ALCHEMY_API_KEY")
            if rpc and "your_alchemy_api_key_here" in rpc and api_key:
                rpc = rpc.replace("your_alchemy_api_key_here", api_key)
            
            if rpc:
                print(f"Fetching dynamic test wallets for {c['symbol']}...")
                addrs = get_dynamic_addresses(rpc, 3)
                for addr in addrs:
                    existing = db.query(MonitoredWallet).filter_by(address=addr).first()
                    if not existing:
                        wallet = MonitoredWallet(
                            address=addr,
                            label=f"Recent {c['symbol']} Activity",
                            chain_id=chain_obj.chain_id,
                            source="dynamic_seed",
                            created_at=datetime.utcnow()
                        )
                        db.add(wallet)
                        db.commit()
                        db.refresh(wallet)
                        print(f"  + Added: {addr[:16]}...")
                        
                        # 初始同步
                        try:
                            sync_wallet(wallet, db)
                        except: pass
        
        print("\nSetup complete! No sensitive whale intelligence was hardcoded.")
        
    finally:
        db.close()

if __name__ == "__main__":
    setup()
