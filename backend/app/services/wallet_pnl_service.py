"""
Wallet PnL Service
==================
Approximate realization logic for PnL and Win Rate based on historical transactions.
Calculates realized, unrealized PnL, Win Rate, and time-bracketed PnL.
"""
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def calculate_pnl(wallet_txs: list, holdings: list) -> dict:
    """
    Given a list of transactions (WalletTransaction) and current holdings (WalletTokenHolding),
    estimate the win rate and PnL across periods.
    
    Returns:
    {
        "win_rate": float, 
        "realized_pnl_usd": float,
        "unrealized_pnl_usd": float,
        "total_pnl_usd": float,
        "periods": {
            "1d": float,
            "3d": float,
            "7d": float,
            "30d": float,
            "60d": float,
            "180d": float,
            "365d": float
        }
    }
    """
    # 1. Very rough approximation of PnL. We will treat IN as costing money (buy) and OUT as gaining fiat (sell).
    # Since we lack precise exact swap pairs, we use the amount_usd on the transaction as the fiat value of that flow.
    # An IN of a token increases the position cost basis.
    # An OUT of a token realizes PnL based on the current average cost.
    
    positions = {} # symbol -> {"amount": float, "cost_basis": float, "realized": float, "wins": int, "losses": int, "trades": int}
    
    # Sort from oldest to newest to build history
    txs_sorted = sorted(wallet_txs, key=lambda x: x.tx_time or datetime.min)
    
    for tx in txs_sorted:
        symbol = tx.asset_symbol or "UNKNOWN"
        if symbol not in positions:
            positions[symbol] = {"amount": 0.0, "cost_basis": 0.0, "realized": 0.0, "wins": 0, "losses": 0, "trades": 0}
            
        amt = float(tx.amount or 0)
        usd = float(tx.amount_usd or 0)
        
        # If it's a native token transfer, labeling it purely as an asset flow.
        if tx.direction == "in":
            # Receiving token -> Assume bought. Cost increases by USD value.
            positions[symbol]["amount"] += amt
            positions[symbol]["cost_basis"] += usd
        elif tx.direction == "out":
            # Sending token -> Assume sold. 
            # Realized PnL = Proceeds (usd) - Cost associated with this portion
            if positions[symbol]["amount"] > 0:
                avg_cost_per_token = positions[symbol]["cost_basis"] / positions[symbol]["amount"]
                cost_of_sold = min(amt, positions[symbol]["amount"]) * avg_cost_per_token
                
                realized = usd - cost_of_sold
                positions[symbol]["realized"] += realized
                
                # Win/Loss tracking closure
                positions[symbol]["trades"] += 1
                if realized > 0:
                    positions[symbol]["wins"] += 1
                else:
                    positions[symbol]["losses"] += 1
                
                # Reduce remaining cost basis and amount
                positions[symbol]["amount"] = max(0, positions[symbol]["amount"] - amt)
                positions[symbol]["cost_basis"] = max(0, positions[symbol]["cost_basis"] - cost_of_sold)
            else:
                # Sold something we don't have record of buying (or it's native token used for gas)
                # Ignore for win tracking to reduce noise
                pass
                
    total_wins = sum(p["wins"] for p in positions.values())
    total_trades = sum(p["trades"] for p in positions.values())
    
    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else None
    realized_total = sum(p["realized"] for p in positions.values())
    
    # Unrealized PnL: from current holdings against the remaining cost basis
    unrealized_total = 0.0
    for h in holdings:
        sym = h.token_symbol or "UNKNOWN"
        est_usd = float(h.estimated_usd or 0)
        if sym in positions:
            cost = positions[sym]["cost_basis"]
            unrealized_total += (est_usd - cost)
            
    # Time periods
    periods = calculate_period_pnl(wallet_txs, holdings, positions)
    
    return {
        "win_rate": round(win_rate, 2) if win_rate is not None else None,
        "realized_pnl_usd": round(realized_total, 2),
        "unrealized_pnl_usd": round(unrealized_total, 2),
        "total_pnl_usd": round(realized_total + unrealized_total, 2),
        "periods": periods
    }

def calculate_period_pnl(wallet_txs: list, holdings: list, state_cache: dict) -> dict:
    """
    Calculate rough net flow change as a proxy for bracketed PnL,
    since true historical token balances at exact past times are difficult without archive nodes.
    We proxy period PnL by summing the realized PnL in that period.
    """
    now = datetime.utcnow()
    brackets = {"1d": 1, "3d": 3, "7d": 7, "30d": 30, "60d": 60, "180d": 180, "365d": 365}
    results = {}
    
    for label, days in brackets.items():
        cutoff = now - timedelta(days=days)
        
        # Realized in this period
        period_txs = [t for t in wallet_txs if t.tx_time and t.tx_time >= cutoff]
        period_realized = 0.0
        
        # Simple netflow proxy for time-based performance
        inflow = sum(float(t.amount_usd or 0) for t in period_txs if t.direction == "in")
        outflow = sum(float(t.amount_usd or 0) for t in period_txs if t.direction == "out")
        net = outflow - inflow # Outflow from wallet is "selling" to get fiat back.

        # Note: net flow is not exactly PnL, but it's an indicative approximation of "extracted" value.
        results[label] = round(net, 2)
        
    return results
