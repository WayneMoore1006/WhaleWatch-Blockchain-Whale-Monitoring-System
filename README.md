# WhaleWatch: 鏈上巨鯨監測系統 🐳(中文介紹)

一個極致專業的多鏈巨鯨錢包監控與預警平台，專為追蹤大額資金流向、分析錢包行為與即時預警而設計。

![WhaleWatch Dashboard](./Demo%20image/螢幕擷取畫面%202026-04-15%20033242.jpg)

## 🚀 平台核心功能

### 📊 戰情監控儀表板 (Intelligence Dashboard)
提供多鏈即時數據概覽，包含 24 小時交易量、資金淨流入/流出趨勢圖，以及最活躍的巨鯨錢包排位。
- **即時數據**: 基於 Alchemy RPC 獲取最新的區塊鏈狀態。
- **可視化圖表**: 使用 Recharts 呈現趨勢變化，一眼掌握市場熱度。

### 📋 巨鯨關注清單 (Watchlist)
集中管理感興趣的錢包地址，支援 Ethereum、BNB Chain (BSC) 與 Solana。
- **自動偵測**: 輸入地址自動識別所屬公鏈。
- **價值評估**: 即時計算錢包總資產價值。
- **動態同步**: 點擊 `Add & Sync` 立即更新錢包快照。

![Watchlist Interface](./Demo%20image/螢幕擷取畫面%202026-04-15%20122148.png)

### 🧠 錢包情報分析 (Wallet Intelligence)
深度的錢包畫像分析，包含持有幣種分佈、交易歷史分類以及精確的損益 (PnL) 統計。
- **標籤系統**: 自動標記地址屬性（如：NFT Whale, MEV Bot）。
- **勝率分析**: 計算交易勝率與盈虧比，找出真正的「聰明錢」。

### 🔔 預警中心 (Alerts Center)
全天候監控鏈上異常活動，整合外部信號與自定義規則。
- **多維度警報**: 支援大額轉帳、資金異動、代幣劇烈波動等警報。
- **智慧過濾**: 根據嚴重程度 (Severity) 分類，減少噪音干擾。

![Alerts Center](./Demo%20image/螢幕擷取畫面%202026-04-15%20014444.jpg)

## 🛠️ 技術棧 (Tech Stack)

### 前端：現代化響應式介面
- **框架**: React 19 + TypeScript (Vite 驅動)
- **樣式**: Tailwind CSS 4 (極致流暢的 UI 體驗)
- **狀態管理**: TanStack Query (React Query) v5
- **圖表庫**: Recharts (專業數據流水線可視化)
- **圖示**: Lucide React & Framer Motion (精緻微交互)

### 後端：高性能異步架構
- **框架**: FastAPI (Python 最佳異步 Web 服務)
- **資料庫**: SQL Server / SQLAlchemy (強大的關聯式存儲)
- **鏈上技術**: Alchemy SDK / Web3.py (多鏈數據整合)
- **定時任務**: APScheduler (自動執行數據同步與清洗)

## 📦 快速安裝與運行

### 1. 後端 (Backend)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
# 複製 .env.example 並填寫您的 ALCHEMY_API_KEY 與資料庫連線
cp .env.example .env 
python app/main.py
```

### 2. 前端 (Frontend)
```bash
cd frontend
npm install
npm run dev
```

## 📂 專案結構細節
```text
├── backend/            # FastAPI 後端
│   ├── app/            # 核心邏輯 (Router: dashboard, watchlist, alerts...)
│   ├── jobs/           # 背景排程 (APScheduler 任務)
│   └── scripts/        # 維護工具 (資料清洗、種子數據)
├── frontend/           # React 前端
│   ├── src/            # 源碼 (Pages, Components, Hooks, API)
│   └── public/         # 靜態資源
└── 資料庫期末專案圖/     # 系統演示圖片集
```

---

## 🔒 私隱與安全
- **環境變數**: 請務必將 `ALCHEMY_API_KEY` 等敏感資訊保存在 `.env` 中，切勿提交至公有倉庫。
- **數據來源**: 本系統所有數據均來自公開區塊鏈帳本，僅供技術研究與模擬分析。

## ⚖️ 免責聲明
> [!WARNING]
> **本專案僅供學術研究與技術展示使用，不構成任何投資建議。**
> 1. 區塊鏈市場具有高風險，請理性投資。
> 2. 系統數據可能存在延誤或第三方 API 錯誤。
> 3. 使用者需自行承擔使用本系統所產生的一切風險與費用。

<br/>
<br/>

---

# WhaleWatch: Blockchain-Whale-Monitoring-System 🐳(English Introduction)

An extremely professional multi-chain whale wallet monitoring and alert platform, designed for tracking large capital flows, analyzing wallet behavior, and providing real-time alerts.

![WhaleWatch Dashboard](./Demo%20image/螢幕擷取畫面%202026-04-15%20033242.jpg)

## 🚀 Core Features

### 📊 Intelligence Dashboard
Provides an overview of multi-chain real-time data, including 24-hour trading volume, net inflow/outflow trends, and rankings of the most active whale wallets.
- **Real-time Data**: Based on Alchemy RPC to obtain the latest blockchain status.
- **Visual Charts**: Uses Recharts to present trend changes, identifying market heat at a glance.

### 📋 Whale Watchlist
Centralized management of wallet addresses of interest, supporting Ethereum, BNB Chain (BSC), and Solana.
- **Auto-detection**: Automatically identifies the corresponding public chain by entering the address.
- **Value Assessment**: Real-time calculation of the total asset value of the wallet.
- **Dynamic Sync**: Click `Add & Sync` to immediately update the wallet snapshot.

![Watchlist Interface](./Demo%20image/螢幕擷取畫面%202026-04-15%20122148.png)

### 🧠 Wallet Intelligence
Deep wallet profiling and analysis, including token holding distribution, transaction history classification, and precise Profit and Loss (PnL) statistics.
- **Tagging System**: Automatically tags address attributes (e.g., NFT Whale, MEV Bot).
- **Win Rate Analysis**: Calculates transaction win rates and risk-reward ratios to find the true "Smart Money."

### 🔔 Alerts Center
24/7 monitoring of on-chain anomaly activities, integrating external signals and custom rules.
- **Multi-dimensional Alerts**: Supports alerts for large transfers, capital movements, token volatility, etc.
- **Smart Filtering**: Classifies by severity levels to reduce noise interference.

![Alerts Center](./Demo%20image/螢幕擷取畫面%202026-04-15%20014444.jpg)

## 🛠️ Tech Stack

### Frontend: Modern Responsive Interface
- **Framework**: React 19 + TypeScript (Vite-powered)
- **Styling**: Tailwind CSS 4 (For ultra-smooth UI experience)
- **State Management**: TanStack Query (React Query) v5
- **Charts**: Recharts (Professional data visualization)
- **Icons & Animation**: Lucide React & Framer Motion

### Backend: High-Performance Asynchronous Architecture
- **Framework**: FastAPI (Python's leading async web framework)
- **Database**: SQL Server / SQLAlchemy (Robust relational storage)
- **On-chain Integration**: Alchemy SDK / Web3.py
- **Task Scheduling**: APScheduler (Automated data synchronization and cleaning)

## 📦 Quick Start

### 1. Backend Setup
```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\activate
source venv/bin/activate
pip install -r requirements.txt
# Copy .env.example and fill in ALCHEMY_API_KEY/DB info
cp .env.example .env 
python app/main.py
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 📂 Project Structure
```text
├── backend/            # FastAPI application
│   ├── app/            # Core logic (Routers, Services, Models)
│   ├── jobs/           # Background tasks (APScheduler)
│   └── scripts/        # Dev & maintenance tools
├── frontend/           # React application
│   ├── src/            # Source code (Pages, Components, Hooks)
│   └── public/         # Static assets
└── Demo image/         # System demonstration screenshots
```

---

## 🔒 Privacy & Security
- **Environments**: Always keep `ALCHEMY_API_KEY` in your `.env` file. Never commit `.env` to public repositories.
- **Data Source**: This system solely reads public blockchain ledger data for research purposes.

## ⚖️ Disclaimer
> [!WARNING]
> **This project is for educational and technical demonstration purposes only. It does not constitute financial advice.**
> 1. Crypto markets are high-risk. Please invest rationally.
> 2. System data may have delays or errors from third-party APIs.
> 3. Users assume all risks and costs associated with using this system.

---
*Powered by Antigravity — Dedicated to providing the most intuitive on-chain data insights.*
