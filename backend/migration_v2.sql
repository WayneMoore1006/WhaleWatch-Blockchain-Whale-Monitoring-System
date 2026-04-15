-- ============================================================
-- Migration V2: 擴充多鏈巨鯨監控系統資料庫 Schema
-- 執行前請確認已連接到 WhaleWatch 資料庫
-- ============================================================

USE WhaleWatch;

-- ──────────────────────────────────────────────────────────────
-- 1. 更新 monitored_wallets 資料表
-- ──────────────────────────────────────────────────────────────
-- 新增欄位（若已存在則跳過）
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('monitored_wallets') AND name = 'masked_address')
    ALTER TABLE monitored_wallets ADD masked_address NVARCHAR(128);

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('monitored_wallets') AND name = 'chain')
    ALTER TABLE monitored_wallets ADD chain NVARCHAR(10);

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('monitored_wallets') AND name = 'source')
    ALTER TABLE monitored_wallets ADD source NVARCHAR(50) DEFAULT 'manual';

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('monitored_wallets') AND name = 'updated_at')
    ALTER TABLE monitored_wallets ADD updated_at DATETIME DEFAULT GETUTCDATE();

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('monitored_wallets') AND name = 'last_synced_at')
    ALTER TABLE monitored_wallets ADD last_synced_at DATETIME;

-- 為現有記錄填入 chain 預設值
UPDATE monitored_wallets SET chain = 'ETH' WHERE chain IS NULL;

-- ──────────────────────────────────────────────────────────────
-- 2. 更新 alerts 資料表
-- ──────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('alerts') AND name = 'chain')
    ALTER TABLE alerts ADD chain NVARCHAR(10);

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('alerts') AND name = 'alert_type')
    ALTER TABLE alerts ADD alert_type NVARCHAR(50);

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('alerts') AND name = 'title')
    ALTER TABLE alerts ADD title NVARCHAR(200);

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('alerts') AND name = 'source')
    ALTER TABLE alerts ADD source NVARCHAR(20) DEFAULT 'watchlist';

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('alerts') AND name = 'related_tx_hash')
    ALTER TABLE alerts ADD related_tx_hash NVARCHAR(128);

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('alerts') AND name = 'metadata_json')
    ALTER TABLE alerts ADD metadata_json NVARCHAR(MAX);

-- 修正 severity 預設值
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('alerts') AND name = 'description')
    ALTER TABLE alerts ADD description NVARCHAR(MAX);

-- ──────────────────────────────────────────────────────────────
-- 3. 建立 wallet_balances 資料表
-- ──────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('wallet_balances'))
BEGIN
    CREATE TABLE wallet_balances (
        id               INT IDENTITY(1,1) PRIMARY KEY,
        wallet_id        INT REFERENCES monitored_wallets(wallet_id) ON DELETE CASCADE,
        chain            NVARCHAR(10) NOT NULL,
        native_symbol    NVARCHAR(10),
        native_balance   DECIMAL(38,18) DEFAULT 0,
        native_balance_usd  DECIMAL(20,2),
        total_estimated_usd DECIMAL(20,2),
        price_source     NVARCHAR(50),
        snapshot_time    DATETIME DEFAULT GETUTCDATE()
    );
    PRINT 'Created wallet_balances';
END;

-- ──────────────────────────────────────────────────────────────
-- 4. 建立 wallet_token_holdings 資料表
-- ──────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('wallet_token_holdings'))
BEGIN
    CREATE TABLE wallet_token_holdings (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        wallet_id       INT REFERENCES monitored_wallets(wallet_id) ON DELETE CASCADE,
        chain           NVARCHAR(10) NOT NULL,
        token_address   NVARCHAR(128),
        token_symbol    NVARCHAR(50),
        token_name      NVARCHAR(200),
        amount          DECIMAL(38,18) DEFAULT 0,
        decimals        INT DEFAULT 18,
        estimated_usd   DECIMAL(20,2),
        price_source    NVARCHAR(50),
        snapshot_time   DATETIME DEFAULT GETUTCDATE()
    );
    PRINT 'Created wallet_token_holdings';
END;

-- ──────────────────────────────────────────────────────────────
-- 5. 建立 wallet_transactions 資料表
-- ──────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('wallet_transactions'))
BEGIN
    CREATE TABLE wallet_transactions (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        wallet_id       INT REFERENCES monitored_wallets(wallet_id) ON DELETE CASCADE,
        chain           NVARCHAR(10) NOT NULL,
        tx_hash         NVARCHAR(128) NOT NULL,
        direction       NVARCHAR(4),        -- 'in' / 'out'
        counterparty    NVARCHAR(128),
        asset_symbol    NVARCHAR(50),
        amount          DECIMAL(38,18) DEFAULT 0,
        amount_usd      DECIMAL(20,2),
        tx_type         NVARCHAR(30),
        block_number    BIGINT,
        tx_time         DATETIME,
        raw_payload_json NVARCHAR(MAX),
        created_at      DATETIME DEFAULT GETUTCDATE()
    );
    CREATE INDEX IX_wt_wallet_time ON wallet_transactions(wallet_id, tx_time DESC);
    CREATE INDEX IX_wt_chain_time  ON wallet_transactions(chain, tx_time DESC);
    PRINT 'Created wallet_transactions';
END;

-- ──────────────────────────────────────────────────────────────
-- 6. 建立 wallet_daily_stats 資料表
-- ──────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('wallet_daily_stats'))
BEGIN
    CREATE TABLE wallet_daily_stats (
        id                  INT IDENTITY(1,1) PRIMARY KEY,
        wallet_id           INT REFERENCES monitored_wallets(wallet_id) ON DELETE CASCADE,
        chain               NVARCHAR(10) NOT NULL,
        stat_date           DATE NOT NULL,
        tx_count            INT DEFAULT 0,
        inflow_usd          DECIMAL(20,2) DEFAULT 0,
        outflow_usd         DECIMAL(20,2) DEFAULT 0,
        netflow_usd         DECIMAL(20,2) DEFAULT 0,
        active_counterparties INT DEFAULT 0,
        CONSTRAINT UQ_daily_stats UNIQUE (wallet_id, chain, stat_date)
    );
    PRINT 'Created wallet_daily_stats';
END;

-- ──────────────────────────────────────────────────────────────
-- 7. 建立 external_alert_feeds 資料表
-- ──────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('external_alert_feeds'))
BEGIN
    CREATE TABLE external_alert_feeds (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        source_name     NVARCHAR(100),
        source_type     NVARCHAR(50),
        is_enabled      BIT DEFAULT 1,
        last_fetched_at DATETIME,
        config_json     NVARCHAR(MAX),
        created_at      DATETIME DEFAULT GETUTCDATE()
    );
    -- 預設插入已知公開來源
    INSERT INTO external_alert_feeds (source_name, source_type, is_enabled, config_json)
    VALUES
        ('coingecko_top_gainers', 'api', 1, '{"endpoint": "https://api.coingecko.com/api/v3/coins/markets", "timeout": 10}'),
        ('dexscreener_trending',  'api', 1, '{"endpoint": "https://api.dexscreener.com/latest/dex/tokens", "timeout": 10}');
    PRINT 'Created external_alert_feeds';
END;

PRINT 'Migration V2 completed successfully.';
