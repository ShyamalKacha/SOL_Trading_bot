# Solana Wallet Balance Documentation

## Overview
This document explains how the wallet balance functionality works in the Solana Trading Bot, including the correct methods for fetching different types of assets from a Solana wallet.

## The Core Understanding

There are THREE different "balances" on Solana, and they come from different RPC calls:

| Asset Type | Where it Lives | How to Fetch |
|------------|----------------|--------------|
| SOL | Native lamports on wallet | `getBalance` |
| SPL tokens (USDC, wSOL, etc.) | Token Accounts | `getTokenAccountsByOwner` |
| NFTs | Metaplex / DAS | `getAssetsByOwner` (Helius DAS) |

## The Correct Architecture

The implementation must handle ALL THREE asset types separately:

### A) SOL Balance (Native)
```python
sol_resp = client.get_balance(pubkey)
sol_balance = sol_resp.value / 1_000_000_000
```

### B) SPL Fungible Tokens (USDC, wSOL, others)
```python
from solana.rpc.types import TokenAccountOpts
from spl.token.constants import TOKEN_PROGRAM_ID

resp = client.get_token_accounts_by_owner(
    pubkey,
    TokenAccountOpts(program_id=TOKEN_PROGRAM_ID)
)

tokens = []

for acc in resp.value:
    info = acc.account.data.parsed["info"]
    mint = info["mint"]
    amount = int(info["tokenAmount"]["amount"])
    decimals = int(info["tokenAmount"]["decimals"])

    balance = amount / (10 ** decimals)

    # Skip zero balances
    if balance == 0:
        continue

    tokens.append({
        "token": mint,     # you can map this to symbol later
        "name": "",
        "mint": mint,
        "balance": balance
    })
```

### C) NFTs (Optional, but handled separately)
Helius DAS: `getAssetsByOwner` - This is handled separately and not mixed with SPL tokens

## Complete Implementation

### 1. RPC Client Configuration
The implementation uses Helius RPC for better performance and reliability:
```python
helius_api_key = os.getenv("HELIUS_API_KEY")
if helius_api_key:
    client = Client(f"https://mainnet.helius-rpc.com/?api-key={helius_api_key}")
else:
    client = Client("https://api.mainnet-beta.solana.com")  # Fallback
```

### 2. SOL Balance (Native)
```python
sol_resp = client.get_balance(pubkey)
sol_balance = sol_resp.value / 1_000_000_000

balances = [{
    "token": "SOL",
    "name": "Solana",
    "mint": "So11111111111111111111111111111111111111112",
    "balance": sol_balance
}]
```

### 3. SPL Token Balances (USDC, wSOL, others)
```python
from solana.rpc.types import TokenAccountOpts
from spl.token.constants import TOKEN_PROGRAM_ID

resp = client.get_token_accounts_by_owner(
    pubkey,
    TokenAccountOpts(program_id=TOKEN_PROGRAM_ID)
)

tokens = []

for acc in resp.value:
    info = acc.account.data.parsed["info"]
    mint = info["mint"]
    amount = int(info["tokenAmount"]["amount"])
    decimals = int(info["tokenAmount"]["decimals"])

    balance = amount / (10 ** decimals)

    # Skip zero balances
    if balance == 0:
        continue

    # Determine token symbol based on mint address
    if mint == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v":  # USDC
        token_symbol = "USDC"
        token_name = "USD Coin"
    elif mint == "So11111111111111111111111111111111111111112":  # wSOL
        token_symbol = "wSOL"
        token_name = "Wrapped Solana"
    else:
        token_symbol = TOKEN_INFO.get(mint, {}).get("symbol", "UNKNOWN")
        token_name = TOKEN_INFO.get(mint, {}).get("name", "Unknown Token")

    tokens.append({
        "token": token_symbol,
        "symbol": token_symbol,
        "name": token_name,
        "mint": mint,
        "balance": balance,
        "decimals": decimals,
        "type": "spl-token"
    })

# Add SPL tokens to balances
balances.extend(tokens)
```

### 4. Final API Response
```python
return jsonify({
    "success": True,
    "balances": balances
})
```

## Key Points

### Why This Architecture is Correct
- **getBalance** provides authoritative SOL balance directly from blockchain
- **getTokenAccountsByOwner** with **TokenAccountOpts** provides accurate SPL token balances
- **getAssetsByOwner** (Helius DAS) provides NFT information
- Indexer APIs like `getAssetsByOwner` are NOT authoritative for balances

### Common Mistakes to Avoid
1. **Don't pass raw dicts** to Solana Py methods - use proper typed objects like `TokenAccountOpts`
2. **Don't mix NFT parsing with SPL token parsing** - they have different data structures
3. **Don't rely solely on indexer APIs** for balance information
4. **Always handle decimals properly** when calculating token balances

### Token Amount Calculation
```python
# Raw amount from RPC is in base units
raw_amount = int(info["tokenAmount"]["amount"])
decimals = int(info["tokenAmount"]["decimals"])
# Convert to display amount
balance = raw_amount / (10 ** decimals)
```

### Mint Address Recognition
- USDC: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`
- wSOL: `So11111111111111111111111111111111111111112` (same as SOL native)
- SOL: `So11111111111111111111111111111111111111112`

### Zero Balance Handling
The implementation skips tokens with zero balance to avoid cluttering the display.

## API Response Format
The `/api/wallet-balance` endpoint returns:
```json
{
  "success": true,
  "balances": [
    {
      "token": "SOL",
      "symbol": "SOL", 
      "name": "Solana",
      "balance": 0.012345678,
      "mint": "So11111111111111111111111111111111111111112",
      "decimals": 9,
      "type": "native"
    },
    {
      "token": "USDC",
      "symbol": "USDC",
      "name": "USD Coin", 
      "balance": 10.50,
      "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
      "decimals": 6,
      "type": "spl-token"
    }
  ]
}
```

## Private Key Handling
The wallet address is derived from the private key stored in the `.env` file using proper base58 decoding:
- For 64-byte keys: `Keypair.from_bytes(secret)`
- For 32-byte keys: `Keypair.from_seed(secret)`

## Troubleshooting
- If SOL balance shows 0, verify private key format and derivation
- If SPL tokens don't appear, check that they have non-zero balances
- If you see "UNKNOWN" tokens, the mint address may not be in the known tokens mapping
- NFTs will not appear in the token balance list (they're a different asset type)
- If you see "UNKNOWN 0.000000 CgcZiaLj..." - this is an NFT, not a fungible token
- If your wallet has no SPL tokens, the response will only show SOL (and NFTs separately)

## Security Notes
- Private keys are loaded from environment variables and never logged
- All RPC calls are made securely over HTTPS
- Token balances are read-only operations that don't require private key access
- Balance checking is performed before each trade to ensure sufficient funds
- Minimum SOL balance (0.005 SOL) is reserved for transaction fees

## Trading Integration
- The trading bot uses wallet balance information to validate sufficient funds before executing trades
- Balance checking occurs before each buy/sell operation to prevent failed transactions
- The bot checks both the token being traded and SOL for transaction fees
- If SOL balance falls below the reserved amount (0.005 SOL), trades are blocked

## Why Helius is Required
- Public RPC: ❌ 403, rate limits, bot blocking
- Helius: ✅ Trading, balances, DAS
- Use Helius for everything on mainnet