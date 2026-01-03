# Jupiter API Documentation

## Quote API (v6)

### Endpoint
`https://quote-api.jup.ag/v6/quote`

### Parameters
- `inputMint` (required): The mint address of the token to swap from
- `outputMint` (required): The mint address of the token to swap to
- `amount` (required): The amount of input token to swap (in base units, e.g., lamports for SOL)
- `slippageBps` (optional): Slippage tolerance in basis points (e.g., 100 for 1%)
- `autoSlippage` (optional): Boolean to enable auto slippage calculation
- `maxAutoSlippageBps` (optional): Max slippage for auto slippage in basis points
- `minSPLTokenToReceive` (optional): Minimum amount of SPL token to receive after swap
- `swapMode` (optional): "ExactIn" or "ExactOut" (default: "ExactIn")

### Example Request
```
GET https://quote-api.jup.ag/v6/quote?inputMint=So11111111111111111111111111111111111111112&outputMint=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v&amount=1000000000
```

## Swap API (v6)

### Endpoint
`https://quote-api.jup.ag/v6/swap`

### Parameters
- `quoteResponse` (required): The quote response from the quote endpoint
- `userPublicKey` (required): The user's public key
- `wrapAndUnwrapSol` (optional): Boolean to wrap/unwrap SOL (default: true)
- `useSharedAccounts` (optional): Boolean for shared accounts (default: true)
- `feeAccount` (optional): Fee account for partner fee
- `dynamicComputeUnitLimit` (optional): Boolean to enable dynamic compute unit limit (default: true)
- `prioritizationFeeLamports` (optional): Priority fee in lamports

### Notes
- Default slippage tolerance is set to 50 basis points (0.5%)
- The trading algorithm uses dual arrays (buy_parts and sell_parts) to manage trading opportunities
- When buying: buy_parts decreases by 1, sell_parts increases by 1 (creating future sell opportunities)
- When selling: sell_parts decreases by 1, buy_parts increases by 1 (creating future buy opportunities)
- Buy operations spend a fixed dollar amount (trade_amount/number_of_parts) to purchase tokens
- Sell operations sell tokens worth a fixed dollar amount (trade_amount/number_of_parts) at current market price
- Transaction fees are reserved (0.005 SOL minimum) and profit calculations account for fees ($0.02 per transaction)
- For simulation purposes, we won't execute real swaps
- We will use the quote API to get pricing information
- SOL mint address: So111111111111111111111111111111111111111112