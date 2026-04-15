-- SQL Server Schema for Whale Wallet Monitoring System

-- Chains Table
CREATE TABLE chains (
    chain_id INT PRIMARY KEY IDENTITY(1,1),
    name NVARCHAR(50) NOT NULL,
    symbol NVARCHAR(10) NOT NULL,
    rpc_url NVARCHAR(255),
    is_active BIT DEFAULT 1
);

-- Monitored Wallets Table
CREATE TABLE monitored_wallets (
    wallet_id INT PRIMARY KEY IDENTITY(1,1),
    address NVARCHAR(128) NOT NULL UNIQUE,
    label NVARCHAR(100),
    chain_id INT FOREIGN KEY REFERENCES chains(chain_id),
    risk_score INT DEFAULT 0,
    is_active BIT DEFAULT 1,
    created_at DATETIME DEFAULT GETDATE(),
    last_activity DATETIME
);

-- Wallet Labels / Tags
CREATE TABLE wallet_labels (
    label_id INT PRIMARY KEY IDENTITY(1,1),
    wallet_id INT FOREIGN KEY REFERENCES monitored_wallets(wallet_id),
    tag NVARCHAR(50) NOT NULL
);

-- Transactions Table
CREATE TABLE transactions (
    tx_id BIGINT PRIMARY KEY IDENTITY(1,1),
    tx_hash NVARCHAR(66) NOT NULL UNIQUE,
    wallet_id INT FOREIGN KEY REFERENCES monitored_wallets(wallet_id),
    from_address NVARCHAR(128),
    to_address NVARCHAR(128),
    value DECIMAL(38, 18),
    gas_used BIGINT,
    block_number BIGINT,
    block_timestamp DATETIME,
    method_name NVARCHAR(100)
);

-- Token Transfers
CREATE TABLE token_transfers (
    transfer_id BIGINT PRIMARY KEY IDENTITY(1,1),
    tx_hash NVARCHAR(66),
    wallet_id INT FOREIGN KEY REFERENCES monitored_wallets(wallet_id),
    token_address NVARCHAR(128),
    token_symbol NVARCHAR(20),
    value DECIMAL(38, 18),
    direction NVARCHAR(10) -- 'IN' or 'OUT'
);

-- Alerts Table
CREATE TABLE alerts (
    alert_id INT PRIMARY KEY IDENTITY(1,1),
    wallet_id INT FOREIGN KEY REFERENCES monitored_wallets(wallet_id),
    type NVARCHAR(50), -- 'LargeTransfer', 'ContractInteraction', etc.
    severity NVARCHAR(20), -- 'High', 'Medium', 'Low'
    description NVARCHAR(MAX),
    tx_hash NVARCHAR(66),
    status NVARCHAR(20) DEFAULT 'new', -- 'new', 'investigating', 'resolved'
    created_at DATETIME DEFAULT GETDATE()
);

-- External Signals
CREATE TABLE external_signals (
    signal_id INT PRIMARY KEY IDENTITY(1,1),
    source NVARCHAR(50), -- 'WhaleAlert', 'Twitter', 'News'
    content NVARCHAR(MAX),
    timestamp DATETIME DEFAULT GETDATE(),
    relevance_score FLOAT
);

-- Daily Metrics for Dashboard
CREATE TABLE daily_chain_metrics (
    metric_id INT PRIMARY KEY IDENTITY(1,1),
    chain_id INT FOREIGN KEY REFERENCES chains(chain_id),
    date DATE,
    total_volume_usd DECIMAL(38, 2),
    active_wallets_count INT,
    large_tx_count INT
);
