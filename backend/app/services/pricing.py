"""
Pricing Service
===============
提供 token USD 估值。主要來源：CoinGecko 免費 API，備援：DexScreener。
查無價格時回傳 None，不得偽造數字。

Performance：in-memory TTL 快取（60 秒）。同一進程內同 symbol 不重複打 API。
"""
import time
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# CoinGecko coin id 對照（native token）
_NATIVE_COIN_IDS = {
    "ETH":  "ethereum",
    "BNB":  "binancecoin",
    "SOL":  "solana",
    "USDT": "tether",
    "USDC": "usd-coin",
    "WETH": "weth",
    "WBNB": "wbnb",
}

_TIMEOUT = 8  # HTTP timeout（秒）

# ── In-memory TTL 快取 ────────────────────────────────────────────────
# 格式: { symbol_upper: (price_float, expires_at_unix) }
_PRICE_CACHE: dict[str, tuple[float, float]] = {}
_CACHE_TTL_SECONDS = 60  # 60 秒快取


def _get_cached(symbol: str) -> Optional[float]:
    """若快取存在且未過期，回傳快取價格；否則回傳 None。"""
    entry = _PRICE_CACHE.get(symbol.upper())
    if entry:
        price, expires_at = entry
        if time.time() < expires_at:
            logger.debug(f"[pricing] cache hit: {symbol.upper()} = ${price}")
            return price
    return None


def _set_cache(symbol: str, price: float):
    """寫入快取，TTL = _CACHE_TTL_SECONDS。"""
    _PRICE_CACHE[symbol.upper()] = (price, time.time() + _CACHE_TTL_SECONDS)


def get_native_price(chain: str) -> Optional[float]:
    """
    取得鏈的原生 token 價格（USD）。
    chain: 'ETH' / 'BSC' / 'SOL'
    """
    symbol_map = {"ETH": "ETH", "BSC": "BNB", "SOL": "SOL"}
    symbol = symbol_map.get(chain.upper())
    if not symbol:
        return None
    return get_price_usd(symbol)


def get_price_usd(symbol: str, chain: str = "ETH") -> Optional[float]:
    """
    取得 token USD 價格。
    1. 先查記憶體快取（60 秒 TTL）
    2. 查 CoinGecko simple/price（免費端點）
    3. 若失敗，嘗試 DexScreener（補充）
    4. 若都失敗，回傳 None
    """
    symbol_upper = symbol.upper()

    # ── 0. 記憶體快取 ──────────────────────────────────────────────
    cached = _get_cached(symbol_upper)
    if cached is not None:
        return cached

    # ── 1. 主來源：CoinGecko ──────────────────────────────────────
    coin_id = _NATIVE_COIN_IDS.get(symbol_upper)
    if coin_id:
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {"ids": coin_id, "vs_currencies": "usd"}
            resp = requests.get(url, params=params, timeout=_TIMEOUT)
            data = resp.json()
            price = data.get(coin_id, {}).get("usd")
            if price is not None:
                price = float(price)
                _set_cache(symbol_upper, price)
                logger.debug(f"[pricing] {symbol_upper} = ${price} (CoinGecko)")
                return price
        except Exception as e:
            logger.warning(f"[pricing] CoinGecko failed for {symbol_upper}: {e}")

    # ── 2. 備援：DexScreener（只適合有 DEX pair 的 token）─────────
    try:
        url = f"https://api.dexscreener.com/latest/dex/search?q={symbol_upper}"
        resp = requests.get(url, timeout=_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                pairs = data.get("pairs", [])
                if pairs:
                    price_str = pairs[0].get("priceUsd")
                    if price_str:
                        price = float(price_str)
                        _set_cache(symbol_upper, price)
                        return price
    except Exception as e:
        logger.warning(f"[pricing] DexScreener symbol lookup failed for {symbol_upper}: {e}")

    logger.info(f"[pricing] No price found for {symbol_upper}, returning None")
    return None


def get_price_by_address(chain: str, address: str) -> Optional[float]:
    """
    透過 token 合約地址取得價格 (DexScreener)。
    address-based lookup 比 symbol-based lookup 準確得多。
    """
    if not address or address.lower() == "native":
        return get_native_price(chain)
        
    cache_key = f"ADDR_{address.upper()}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
        resp = requests.get(url, timeout=_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                pairs = data.get("pairs", [])
                if pairs:
                    price_str = pairs[0].get("priceUsd")
                    if price_str:
                        price = float(price_str)
                        _set_cache(cache_key, price)
                        return price
    except Exception as e:
        logger.warning(f"[pricing] DexScreener address lookup failed for {address}: {e}")

    return None


def estimate_usd(amount: float, symbol: str, chain: str = "ETH", address: str = None) -> tuple[Optional[float], str]:
    """
    計算估值。回傳 (estimated_usd, price_source)。
    優先使用 address 查詢，其次 symbol。
    """
    price = None
    source = "unavailable"
    
    # 1. 優先用地址查
    if address:
        price = get_price_by_address(chain, address)
        if price: source = "dexscreener_addr"
        
    # 2. 備援用 symbol 查
    if not price:
        price = get_price_usd(symbol, chain)
        if price: source = "coingecko/dex_sym"
        
    if price is None:
        return None, "unavailable"
        
    return round(amount * price, 2), source
