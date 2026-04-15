"""
APScheduler Jobs
=================
定期同步任務，透過 FastAPI lifespan 啟動。
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.database import SessionLocal
from app.services import alert_engine, external_alert_ingestor
from app.services.dashboard_aggregation import get_overview
from app.repositories.wallet_repo import WalletRepository
from app.services.wallet_sync import sync_wallet
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

_scheduler = None


def _get_db():
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def sync_all_wallets_job():
    """每 3 分鐘：並行同步所有 active wallets。"""
    db = SessionLocal()
    try:
        repo = WalletRepository(db)
        wallets = repo.get_active_wallets()
        if not wallets:
            logger.info("[scheduler] sync_wallets: No active wallets")
            return

        # 定義單一錢包同步的包裝函式（每個 thread 使用獨立 Session）
        def _sync_single_wallet(wid):
            worker_db = SessionLocal()
            try:
                repo_w = WalletRepository(worker_db)
                wallet = repo_w.get_wallet_by_id(wid)
                if wallet:
                    sync_wallet(wallet, worker_db)
            except Exception as e:
                logger.error(f"[scheduler] worker sync failed for id {wid}: {e}")
            finally:
                worker_db.close()

        # 並行同步（限制 5 個並發，避免 RPC 過載）
        wallet_ids = [w.wallet_id for w in wallets]
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(_sync_single_wallet, wallet_ids)

        logger.info(f"[scheduler] sync_wallets: Parallel Sync Done ({len(wallets)} wallets)")
    except Exception as e:
        logger.error(f"[scheduler] sync_wallets job error: {e}")
    finally:
        db.close()


def run_alert_engine_job():
    """每 5 分鐘：掃描 alert 條件。"""
    db = SessionLocal()
    try:
        count = alert_engine.run(db)
        logger.info(f"[scheduler] alert_engine: {count} new alerts")
    except Exception as e:
        logger.error(f"[scheduler] alert_engine job error: {e}")
    finally:
        db.close()


def ingest_external_alerts_job():
    """每 30 分鐘：拉取外部訊號。"""
    db = SessionLocal()
    try:
        count = external_alert_ingestor.run(db)
        logger.info(f"[scheduler] external_ingestor: {count} new alerts")
    except Exception as e:
        logger.error(f"[scheduler] external ingestor job error: {e}")
    finally:
        db.close()


def start_scheduler():
    """啟動 APScheduler。由 main.py lifespan 呼叫。"""
    global _scheduler
    _scheduler = BackgroundScheduler()

    # 同步 active wallets — 每 3 分鐘
    _scheduler.add_job(sync_all_wallets_job, IntervalTrigger(minutes=3), id="sync_wallets",
                       replace_existing=True, misfire_grace_time=60)

    # Alert engine — 每 5 分鐘
    _scheduler.add_job(run_alert_engine_job, IntervalTrigger(minutes=5), id="alert_engine",
                       replace_existing=True, misfire_grace_time=60)

    # External alerts — 每 30 分鐘
    _scheduler.add_job(ingest_external_alerts_job, IntervalTrigger(minutes=30), id="external_ingestor",
                       replace_existing=True, misfire_grace_time=120)

    _scheduler.start()
    logger.info("[scheduler] APScheduler started: sync(3m), alerts(5m), external(30m)")


def stop_scheduler():
    """停止 APScheduler。由 main.py lifespan shutdown 呼叫。"""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[scheduler] APScheduler stopped")
