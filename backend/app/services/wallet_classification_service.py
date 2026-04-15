"""
Wallet Classification Service
=============================
Provides basic transaction classification heuristics:
transfer, swap, buy, sell, approve, contract_interaction.
"""
import logging

logger = logging.getLogger(__name__)

# Basic ERC20 Method Signatures
SIG_APPROVE = "0x095ea7b3"
SIG_TRANSFER = "0xa9059cbb"
SIG_TRANSFER_FROM = "0x23b872dd"

# Swap related (Uniswap V2/V3 Router generic methods)
# This is a very rough list, covering exact, exactETH, etc.
SWAP_SIGS = [
    "0x38ed1739", "0x18cbafe5", "0x7ff36ab5", "0x8803dbee",
    "0x5c11d795", "0x4a25d94a", "0x791ac947", "0xfb3bdb41",
    "0xb6f9de95"  # Some 1inch/Paraswap routers
]

def classify_transaction(tx_raw: dict, wallet_address: str) -> str:
    """
    Classify transaction based on raw payload.
    Types: 'transfer', 'approve', 'swap', 'contract_interaction', 'unknown'
    Since we don't have full event logs, 'buy'/'sell' might fall under 'swap'.
    """
    if not tx_raw:
        return "transfer"
        
    wallet_address_lower = wallet_address.lower()
    from_addr = (tx_raw.get("from") or tx_raw.get("from_address") or "").lower()
    to_addr = (tx_raw.get("to") or tx_raw.get("to_address") or "").lower()
    
    # Check "category" if available (e.g. from Alchemy getAssetTransfers)
    category = tx_raw.get("category")
    if category == "erc20" and tx_raw.get("rawContract"):
        # Could be token transfer
        return "transfer"
    
    # Payload input data
    input_data = tx_raw.get("input") or tx_raw.get("data") or "0x"
    input_data = str(input_data).lower()
    
    if input_data == "0x" or input_data == "":
        # Simple native transfer
        return "transfer"
        
    if len(input_data) >= 10:
        sig = input_data[:10]
        
        if sig == SIG_APPROVE:
            return "approve"
            
        if sig == SIG_TRANSFER or sig == SIG_TRANSFER_FROM:
            return "transfer"
            
        if sig in SWAP_SIGS:
            # We can try to guess buy/sell from value and directions, but generally call it swap
            # If native value is > 0 and we are swapping, it's likely buying a token with native (Buy)
            value = tx_raw.get("value") or tx_raw.get("amount") or 0
            try:
                if float(value) > 0 and from_addr == wallet_address_lower:
                    return "buy"  # Exchanging native for token loosely speaking
            except:
                pass
            return "swap"
            
    # Fallback to contract interaction if there's data and it doesn't match known signatures
    return "contract_interaction"

