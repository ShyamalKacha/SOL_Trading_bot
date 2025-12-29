# Solana Wallet Balance Documentation

## Overview
This document explains how the wallet balance functionality works in the Solana Trading Bot, including the correct methods for fetching different types of assets from a Solana wallet.

## Solana Asset Types

Solana wallets can hold three different types of assets, each requiring different RPC calls to fetch:

| Asset Type | Where it Lives | How to Fetch |
|------------|----------------|--------------|
| SOL | Native lamports on wallet | `getBalance` |
| SPL Tokens (USDC, wSOL, etc.) | Token Accounts | `getTokenAccountsByOwner` |
| NFTs | Metaplex / DAS | `getAssetsByOwner` (Helius DAS) |

## Implementation Architecture

### 1. SOL Balance (Native)
```python
sol_resp = client.get_balance(pubkey)
sol_balance = sol_resp.value / 1_000_000_000
```

### 2. SPL Token Balances (USDC, wSOL, others)
```python
from solana.rpc.types import TokenAccountOpts
from spl.token.constants import TOKEN_PROGRAM_ID

resp = client.get_token_accounts_by_owner(
    pubkey,
    TokenAccountOpts(program_id=TOKEN_PROGRAM_ID)
)

for acc in resp.value:
    info = acc.account.data.parsed["info"]
    mint = info["mint"]
    amount = int(info["tokenAmount"]["amount"])
    decimals = int(info["tokenAmount"]["decimals"])
    balance = amount / (10 ** decimals)
    
    # Skip zero balances
    if balance == 0:
        continue
```

### 3. RPC Client Configuration
The implementation uses Helius RPC for better performance and reliability:
```python
helius_api_key = os.getenv("HELIUS_API_KEY")
if helius_api_key:
    client = Client(f"https://mainnet.helius-rpc.com/?api-key={helius_api_key}")
else:
    client = Client("https://api.mainnet-beta.solana.com")  # Fallback
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

## Security Notes
- Private keys are loaded from environment variables and never logged
- All RPC calls are made securely over HTTPS
- Token balances are read-only operations that don't require private key access

## Complete Implementation
The complete implementation in `app/main.py` includes:
- Proper imports for all required libraries
- Error handling for all RPC calls
- Fallback to public RPC if Helius API key is not available
- Proper token symbol and name mapping
- Correct decimal handling for all token types