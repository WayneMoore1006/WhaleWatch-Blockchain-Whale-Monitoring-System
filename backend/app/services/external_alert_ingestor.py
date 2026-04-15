"""
External Alert Ingestor Service
================================
從公開免費來源擷取訊號，寫入 alerts 表（source='external'）。
失敗時記 log、不中斷主服務。

目前整合來源：
  1. CoinGecko /coins/markets — 篩選大幅漲跌（>20%）的代幣
  2. DexScreener /dex/tokens/trending — 篩選高 volume 異常
"""
import json
import logging
import requests
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.models import Alert, ExternalAlertFeed

logger = logging.getLogger(__name__)
_TIMEOUT = 10  # 所有 HTTP 請求 timeout


def _mark_feed_fetched(source_name: str, db: Session):
    """更新 external_alert_feeds.last_fetched_at。"""
    feed = db.query(ExternalAlertFeed).filter_by(source_name=source_name).first()
    if feed:
        feed.last_fetched_at = datetime.utcnow()


def _save_external_alert(chain: str, alert_type: str, severity: str,
                          title: str, description: str, metadata: dict, db: Session):
    """寫入一筆外部訊號。"""
    alert = Alert(
        wallet_id=None,       # 外部訊號無對應 watchlist 地址
        chain=chain,
        alert_type=alert_type,
        severity=severity,
        title=title,
        description=description,
        source="external",
        status="new",
        metadata_json=json.dumps(metadata, default=str),
        created_at=datetime.utcnow()
    )
    db.add(alert)
    logger.info(f"[external_ingestor] Saved external alert: {title[:60]}")


def ingest_coingecko_movers(db: Session):
    """
    來源：CoinGecko /coins/markets（免費）
    篩選：24h 漲跌超過 20% 的 top 100 幣
    """
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 100,
            "page": 1,
            "price_change_percentage": "24h"
        }
        resp = requests.get(url, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        coins = resp.json()

        count = 0
        for coin in coins:
            change_24h = coin.get("price_change_percentage_24h") or 0
            if abs(change_24h) < 20:   # 只取漲跌超過 20% 的
                continue

            symbol = coin.get("symbol", "?").upper()
            price_usd = coin.get("current_price", 0)
            direction = "surged" if change_24h > 0 else "crashed"
            severity = "high" if abs(change_24h) > 30 else "medium"

            _save_external_alert(
                chain="ETH",  # CoinGecko 主要是 EVM
                alert_type="PRICE_SPIKE" if change_24h > 0 else "PRICE_CRASH",
                severity=severity,
                title=f"{symbol} {direction} {change_24h:+.1f}% in 24h",
                description=f"{coin.get('name', symbol)} price {direction} {change_24h:+.1f}% to ${price_usd:,.4f} USD.",
                metadata={"coin_id": coin.get("id"), "symbol": symbol, "price_usd": price_usd, "change_24h": change_24h, "market_cap": coin.get("market_cap")},
                db=db
            )
            count += 1

        _mark_feed_fetched("coingecko_top_gainers", db)
        logger.info(f"[external_ingestor] CoinGecko: {count} alerts generated")

    except requests.exceptions.Timeout:
        logger.warning("[external_ingestor] CoinGecko request timed out")
    except requests.exceptions.HTTPError as e:
        logger.warning(f"[external_ingestor] CoinGecko HTTP error: {e}")
    except Exception as e:
        logger.error(f"[external_ingestor] CoinGecko unexpected error: {e}", exc_info=True)


def ingest_dexscreener_trending(db: Session):
    """
    來源：DexScreener /dex/search（免費）
    目前取前 5 個 trending pair 作為訊號
    """
    try:
        # DexScreener trending pairs for ETH/BSC
        for chain_name, chain_slug in [("ETH", "ethereum"), ("BSC", "bsc")]:
            url = f"https://api.dexscreener.com/latest/dex/tokens/trending"
            resp = requests.get(url, timeout=_TIMEOUT)
            if resp.status_code != 200:
                continue
            pairs = resp.json().get("pairs", [])[:5]

            for pair in pairs:
                base = pair.get("baseToken", {})
                symbol = base.get("symbol", "?")
                volume_24h = pair.get("volume", {}).get("h24", 0) or 0
                price_change = pair.get("priceChange", {}).get("h24", 0) or 0

                if volume_24h < 500_000:   # 只取日交易量超過 $500k 的
                    continue

                _save_external_alert(
                    chain=chain_name,
                    alert_type="HIGH_DEX_VOLUME",
                    severity="medium",
                    title=f"{symbol} High DEX Volume — ${volume_24h:,.0f}",
                    description=f"{symbol} on {pair.get('dexId','?')} has ${volume_24h:,.0f} 24h volume. Price change: {price_change:+.1f}%.",
                    metadata={"pair_address": pair.get("pairAddress"), "dex": pair.get("dexId"), "volume_24h": volume_24h, "price_change_24h": price_change},
                    db=db
                )

        _mark_feed_fetched("dexscreener_trending", db)

    except requests.exceptions.Timeout:
        logger.warning("[external_ingestor] DexScreener request timed out")
    except Exception as e:
        logger.error(f"[external_ingestor] DexScreener error: {e}", exc_info=True)


def run(db: Session) -> int:
    """
    執行所有外部訊號擷取。任一來源失敗不影響其他來源。
    """
    count_before = db.query(Alert).filter_by(source="external").count()

    ingest_coingecko_movers(db)
    ingest_dexscreener_trending(db)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[external_ingestor] Commit failed: {e}")

    count_after = db.query(Alert).filter_by(source="external").count()
    new_count = count_after - count_before
    logger.info(f"[external_ingestor] Run complete. {new_count} new external alerts.")
    return new_count
