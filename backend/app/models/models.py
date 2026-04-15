"""
Database models for the Multi-Chain Whale Monitoring System.
Supports ETH, BSC, SOL chains. All models map to SQL Server tables.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, DECIMAL,
    ForeignKey, BIGINT, Float, Date, Text, JSON, Index, Unicode
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class MonitoredWallet(Base):
    """核心追蹤錢包表 — 儲存所有 watchlist 地址"""
    __tablename__ = "monitored_wallets"

    wallet_id = Column(Integer, primary_key=True, index=True)
    address = Column(String(128), unique=True, nullable=False)
    masked_address = Column(String(128))           # 前端可切換的遮罩版本
    chain = Column(String(10), nullable=False)      # 'ETH' / 'BSC' / 'SOL'
    is_active = Column(Boolean, default=True)
    label = Column(Unicode(100))
    source = Column(String(50), default="manual")   # 'manual' / 'seed' / 'import'
    risk_score = Column(Integer, default=0)
    sort_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced_at = Column(DateTime)
    last_activity = Column(DateTime)

    # Relationships
    balances = relationship("WalletBalance", back_populates="wallet", cascade="all, delete-orphan")
    token_holdings = relationship("WalletTokenHolding", back_populates="wallet", cascade="all, delete-orphan")
    transactions = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")
    daily_stats = relationship("WalletDailyStat", back_populates="wallet", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="wallet")


class WalletBalance(Base):
    """錢包餘額快照 — 每次同步後寫入新快照"""
    __tablename__ = "wallet_balances"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("monitored_wallets.wallet_id", ondelete="CASCADE"))
    chain = Column(String(10), nullable=False)
    native_symbol = Column(String(10))              # ETH / BNB / SOL
    native_balance = Column(DECIMAL(38, 18), default=0)
    native_balance_usd = Column(DECIMAL(20, 2))     # 可為 NULL 若無價格
    total_estimated_usd = Column(DECIMAL(20, 2))    # 含 token 估值
    price_source = Column(String(50))               # 'coingecko' / 'dexscreener'
    snapshot_time = Column(DateTime, default=datetime.utcnow)

    wallet = relationship("MonitoredWallet", back_populates="balances")

    __table_args__ = (
        Index('ix_wallet_balances_lookup', 'wallet_id', 'chain', 'snapshot_time'),
    )


class WalletTokenHolding(Base):
    """錢包 Token 持倉快照"""
    __tablename__ = "wallet_token_holdings"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("monitored_wallets.wallet_id", ondelete="CASCADE"))
    chain = Column(String(10), nullable=False)
    token_address = Column(String(128))
    token_symbol = Column(Unicode(50))
    token_name = Column(Unicode(200))
    amount = Column(DECIMAL(38, 18), default=0)
    decimals = Column(Integer, default=18)
    estimated_usd = Column(DECIMAL(20, 2))          # 可為 NULL 若無價格
    price_source = Column(String(50))
    snapshot_time = Column(DateTime, default=datetime.utcnow)

    wallet = relationship("MonitoredWallet", back_populates="token_holdings")


class WalletTransaction(Base):
    """標準化後的交易紀錄 — 支援 ETH/BSC/SOL"""
    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("monitored_wallets.wallet_id", ondelete="CASCADE"))
    chain = Column(String(10), nullable=False)
    tx_hash = Column(String(128), nullable=False)
    direction = Column(String(4))                   # 'in' / 'out'
    counterparty = Column(String(128))              # 對手地址
    asset_symbol = Column(String(50))               # ETH / USDT / etc.
    amount = Column(DECIMAL(38, 18), default=0)
    amount_usd = Column(DECIMAL(20, 2))             # 可為 NULL
    tx_type = Column(String(30))                    # 'transfer' / 'swap' / 'contract'
    block_number = Column(BIGINT)
    tx_time = Column(DateTime)
    raw_payload_json = Column(Text)                 # 原始 RPC 回傳（JSON string）
    created_at = Column(DateTime, default=datetime.utcnow)

    wallet = relationship("MonitoredWallet", back_populates="transactions")

    __table_args__ = (
        Index('ix_wallet_txs_lookup', 'wallet_id', 'chain', 'tx_time'),
        Index('ix_wallet_txs_hash', 'wallet_id', 'tx_hash'),
    )


class WalletDailyStat(Base):
    """每日彙總統計 — Dashboard 圖表資料來源"""
    __tablename__ = "wallet_daily_stats"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("monitored_wallets.wallet_id", ondelete="CASCADE"))
    chain = Column(String(10), nullable=False)
    stat_date = Column(Date, nullable=False)
    tx_count = Column(Integer, default=0)
    inflow_usd = Column(DECIMAL(20, 2), default=0)
    outflow_usd = Column(DECIMAL(20, 2), default=0)
    netflow_usd = Column(DECIMAL(20, 2), default=0)
    active_counterparties = Column(Integer, default=0)

    wallet = relationship("MonitoredWallet", back_populates="daily_stats")

    __table_args__ = (
        Index('ix_daily_stats_lookup', 'wallet_id', 'chain', 'stat_date'),
    )


class Alert(Base):
    """警報表 — 包含 watchlist 內部警報與外部公開訊號"""
    __tablename__ = "alerts"

    alert_id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("monitored_wallets.wallet_id"), nullable=True)
    chain = Column(String(10))
    alert_type = Column(String(50))                 # LARGE_TRANSFER_IN / HIGH_FREQUENCY / etc.
    severity = Column(String(20), default="medium") # low / medium / high
    title = Column(Unicode(200))
    description = Column(Unicode(MAX) if 'MAX' in locals() else Text)
    source = Column(String(20), default="watchlist")# watchlist / external
    status = Column(String(20), default="new")      # new / read / archived
    related_tx_hash = Column(String(128))
    metadata_json = Column(Text)                    # 額外資料（JSON string）
    created_at = Column(DateTime, default=datetime.utcnow)

    wallet = relationship("MonitoredWallet", back_populates="alerts")

    __table_args__ = (
        Index('ix_alerts_status_chain', 'status', 'chain'),
        Index('ix_alerts_wallet_status', 'wallet_id', 'status'),
    )


class ExternalAlertFeed(Base):
    """外部訊號來源設定表"""
    __tablename__ = "external_alert_feeds"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(100))               # 'coingecko' / 'dexscreener' / etc.
    source_type = Column(String(50))                # 'api' / 'rss' / 'webhook'
    is_enabled = Column(Boolean, default=True)
    last_fetched_at = Column(DateTime)
    config_json = Column(Text)                      # 設定參數（JSON string）
    created_at = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────
# Legacy table kept for reference — will be phased out
# ──────────────────────────────────────────────────────────────
class DailyChainMetric(Base):
    """舊版鏈統計表 — 保留相容性，新版用 wallet_daily_stats"""
    __tablename__ = "daily_chain_metrics"

    metric_id = Column(Integer, primary_key=True, index=True)
    chain = Column(String(10))
    date = Column(Date)
    total_volume_usd = Column(DECIMAL(38, 2))
    active_wallets_count = Column(Integer)
    large_tx_count = Column(Integer)
