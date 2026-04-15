"""
FastAPI Application Entry Point
=================================
Registers all routers and initializes APScheduler via lifespan.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.routers import dashboard, watchlist, wallet_intelligence_router, alerts
from app.core.database import Base, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命週期：啟動/停止 APScheduler。"""
    # 建立 DB tables（若不存在）
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("[startup] DB tables checked/created")
    except Exception as e:
        logger.warning(f"[startup] DB create_all warning (may be OK if tables exist): {e}")

    # 啟動 scheduler
    try:
        from jobs.scheduler import start_scheduler
        start_scheduler()
        logger.info("[startup] Scheduler started")
    except Exception as e:
        logger.error(f"[startup] Scheduler failed to start: {e}")

    yield  # ← 應用程式正常運行

    # 停止 scheduler
    try:
        from jobs.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass


app = FastAPI(
    title="Whale Wallet Monitoring System API",
    description="Multi-chain whale monitoring: ETH / BSC / SOL",
    version="2.0.0",
    lifespan=lifespan
)

# CORS（開發環境允許所有來源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# GZip 壓縮（減少大量陣列或 JSON 時的傳輸延遲）
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── API Routers ──────────────────────────────────────────────
app.include_router(dashboard.router)
app.include_router(watchlist.router)
app.include_router(wallet_intelligence_router.router)
app.include_router(alerts.router)
app.include_router(alerts.external_router)


@app.get("/")
async def root():
    return {"message": "Whale Monitoring API v2.0 — ETH / BSC / SOL"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}
