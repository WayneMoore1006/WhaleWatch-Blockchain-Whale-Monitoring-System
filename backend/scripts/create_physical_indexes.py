"""
建立物理 DB 索引腳本 (Physical DB Index Creation)
確保模型上定義的 composite indexes 在資料庫端實際建立。
"""
from app.core.database import engine
from app.models.models import Base
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQL Server 中建 Index 可以直接用 CREATE INDEX，但為避免報錯「已存在」，可以加上簡單的包裹檢查
index_statements = [
    """
    IF NOT EXISTS (SELECT name FROM sys.indexes WHERE name = 'ix_wallet_balances_lookup')
    CREATE INDEX ix_wallet_balances_lookup ON wallet_balances(wallet_id, chain, snapshot_time);
    """,
    """
    IF NOT EXISTS (SELECT name FROM sys.indexes WHERE name = 'ix_wallet_txs_lookup')
    CREATE INDEX ix_wallet_txs_lookup ON wallet_transactions(wallet_id, chain, tx_time);
    """,
    """
    IF NOT EXISTS (SELECT name FROM sys.indexes WHERE name = 'ix_wallet_txs_hash')
    CREATE INDEX ix_wallet_txs_hash ON wallet_transactions(wallet_id, tx_hash);
    """,
    """
    IF NOT EXISTS (SELECT name FROM sys.indexes WHERE name = 'ix_daily_stats_lookup')
    CREATE INDEX ix_daily_stats_lookup ON wallet_daily_stats(wallet_id, chain, stat_date);
    """,
    """
    IF NOT EXISTS (SELECT name FROM sys.indexes WHERE name = 'ix_alerts_status_chain')
    CREATE INDEX ix_alerts_status_chain ON alerts(status, chain);
    """,
    """
    IF NOT EXISTS (SELECT name FROM sys.indexes WHERE name = 'ix_alerts_wallet_status')
    CREATE INDEX ix_alerts_wallet_status ON alerts(wallet_id, status);
    """
]

def create_physical_indexes():
    with engine.begin() as conn:
        for stmt in index_statements:
            logger.info("Executing index statement...")
            conn.execute(text(stmt))
    logger.info("All indexes ensured successfully.")

if __name__ == "__main__":
    create_physical_indexes()
