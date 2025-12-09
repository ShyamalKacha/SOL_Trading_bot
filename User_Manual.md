# Solana Trading Bot - User Manual

## Table of Contents
1. [Getting Started](#getting-started)
2. [Wallet Connection](#wallet-connection)
3. [Trading Configuration](#trading-configuration)
4. [Trading Logic Explained](#trading-logic-explained)
5. [Monitoring and Controls](#monitoring-and-controls)
6. [Supported Tokens](#supported-tokens)
7. [Troubleshooting](#troubleshooting)
8. [Safety and Security](#safety-and-security)

---

## Getting Started

### Prerequisites
Before using the Solana Trading Bot, ensure you have:

1. **Phantom Wallet** installed in your browser
2. **Tokens in your wallet** for testing/operation
3. A **modern web browser** (Chrome, Firefox, or Edge)
4. **Stable internet connection** for API access

### Starting the Application
1. Locate the `run_app.bat` file in the application directory
2. Double-click the batch file to start the application
3. Wait for the message "Running on http://127.0.0.1:5000"
4. Open your browser and navigate to `http://localhost:5000`
5. The application interface will load and is ready for use

---

## Wallet Connection

### Connecting Your Wallet

1. **Locate the Wallet Section**: Find the "Wallet Connection" panel on the left side of the interface

2. **Click Connect Button**: 
   - Click the **"Connect Wallet"** button
   - A Phantom wallet prompt will appear
   - Select your wallet and approve the connection
   - Status will change to "Connected" with your wallet address

3. **Verify Connection**:
   - Status badge turns green with "Connected" text
   - Wallet address shows (first and last 4 characters)
   - Token balances appear in the balance display area

### Network Selection
- Use the **"Network"** dropdown to select:
  - **Mainnet**: For real trading (tokens have actual value)
  - **Devnet**: For testing with fake tokens
  - **Testnet**: For testing with fake tokens
- Select the network that matches your wallet's current network

### Disconnecting Wallet
- Click the **"Connect Wallet"** button again when already connected
- The wallet will disconnect and balances will clear

---

## Trading Configuration

### Token Selection

**Option 1: Predefined Tokens**
1. Use the dropdown menu labeled **"Select Token"**
2. Choose from available options:
   - SOL (Solana native token)
   - wSOL (Wrapped Solana)
   - USDC (USD Coin)

**Option 2: Custom Tokens**
1. Enter the token's mint address in the **"Or Enter Custom Token Address"** field
2. Example addresses:
   - Franklin: `CSrwNk6B1DwWCHRMsaoDVUfD5bBMQCJPY72ZG3Nnpump`
   - wSOL: `So11111111111111111111111111111111111111112`
3. The custom address takes priority over dropdown selection

### Setting Trading Parameters

#### Base Price
1. Enter the reference price in the **"Base Price ($)"** field
2. This is your benchmark price for trading decisions
3. Example: If SOL is trading at $130, you might set base price to $130

#### Sell Percentages
1. **Sell High Percentage**: Enter percentage above base price to trigger sell
   - Field: **"Sell High Percentage (%)"**
   - Example: Enter `5` for 5% above base price
2. **Sell Low Percentage**: Enter percentage below base price to trigger sell  
   - Field: **"Sell Low Percentage (%)"**
   - Example: Enter `3` for 3% below base price

#### Trade Amount
1. Enter the quantity to trade in the **"Trade Amount"** field
2. This is how much of the token you want to buy/sell per transaction
3. Example: Enter `5` to trade 5 tokens at a time

### Starting Trading

1. **Verify Settings**: Ensure all parameters are correctly set
2. **Click Start**: Press the **"Start Trading"** button (green)
3. **Monitor Status**: Check the "Trading Status" panel for real-time updates
4. **Watch History**: View executed trades in the "Transaction History" table

### Stopping Trading

1. Click the **"Stop Trading"** button (red)
2. Trading will stop immediately
3. All settings are preserved for next use

---

## Trading Logic Explained

### Buy Conditions
The bot will **BUY** when:
- **Current Price < Base Price** AND
- **Last action was NOT a buy**

**Example**:
- Base Price: $100
- Current Price: $98
- Action: BUY (if last action was not buy)

### Sell Conditions  
The bot will **SELL** when:
- **Current Price >= Base Price × (1 + Sell High %)** OR
- **Current Price <= Base Price × (1 - Sell Low %)** 
AND
- **Last action was NOT a sell**

**Example**:
- Base Price: $100
- Sell High %: 5%
- Sell Low %: 3%
- Sell High Threshold: $100 × 1.05 = $105
- Sell Low Threshold: $100 × 0.97 = $97
- Will SELL if price ≥ $105 OR price ≤ $97

### Important Trading Rules

#### No Consecutive Same Actions
- The bot will NOT buy immediately after a buy
- The bot will NOT sell immediately after a sell
- Each action type (buy/sell) must alternate

#### Real Trading Example
1. **Initial State**: Price=$132.50, Base=$133.00, Sell High=10%, Sell Low=5%
2. **Price drops** to $132.90 → **BUY** executes (price < base)
3. **Price rises** to $140.00 → **SELL** executes (price > $146.30 threshold)  
4. **Price drops** to $132.80 → **BUY** executes (price < $133.00 base)
5. **Price rises** to $134.00 → **NO TRADE** (not above $146.30 threshold)

---

## Monitoring and Controls

### Status Panel Information

#### Status Indicator
- **Green Circle**: Trading is active
- **Red Circle**: Trading is stopped
- **Text**: "Running" or "Stopped"

#### Current Price
- Displays real-time price of your selected token
- Updates every 5 seconds when trading is active
- Shows with up to 8 decimal places for precision

#### Last Action
- Shows the most recent trade action (Buy/Sell)
- Includes the token and price of the last transaction

#### Last Updated  
- Shows the timestamp of the last price update
- Helps verify the data is current

### Transaction History

#### Table Columns
- **Time**: When the transaction occurred
- **Action**: Buy or Sell
- **Token**: Which token was traded (abbreviated)
- **Price**: Price at which transaction occurred
- **Amount**: Quantity of tokens traded

#### History Display
- Shows the last 20 transactions
- Most recent transactions appear at the top
- Color-coded: Green for buys, Red for sells

---

## Supported Tokens

### Predefined Tokens
The following tokens are available in the dropdown:

| Symbol | Name | Mint Address |
|--------|------|--------------|
| SOL | Solana | So11111111111111111111111111111111111111112 |
| wSOL | Wrapped Solana | So11111111111111111111111111111111111111112 |
| USDC | USD Coin | EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v |

**Note**: SOL and wSOL share the same mint address but are treated the same by the bot.

### Custom Tokens
You can trade any Solana SPL token by entering its mint address:

1. **Format**: 32-44 character base58 string
2. **Validation**: System verifies address format
3. **Examples**: 
   - Meme tokens (like Franklin)
   - Project-specific tokens
   - Any SPL token with liquidity on Jupiter

### Price Precision
- Prices display up to 8 decimal places
- System accounts for token decimals automatically
- SOL uses 9 decimals, USDC uses 6 decimals

---

## Troubleshooting

### Common Issues

#### Wallet Won't Connect
**Problem**: Clicking "Connect Wallet" does nothing
**Solutions**:
1. Ensure Phantom wallet extension is installed and unlocked
2. Check that no other apps are using your wallet
3. Refresh the browser page
4. Try a different browser

#### Prices Show as 0.00
**Problem**: Current price displays as $0.00
**Solutions**:
1. Check internet connection
2. Verify the selected token has liquidity on Jupiter
3. Try selecting a different token
4. Check browser console for API errors

#### Trading Not Starting
**Problem**: Clicking "Start Trading" has no effect
**Solutions**:
1. Verify wallet is connected
2. Ensure all trading parameters are set
3. Check browser console for errors
4. Refresh page and try again

#### Custom Token Not Working
**Problem**: Custom token address not accepted
**Solutions**:
1. Verify address is 32-44 characters long
2. Confirm the token exists on Solana blockchain
3. Ensure token has liquidity on Jupiter
4. Try a known working address for testing

### Network-Specific Issues

#### Devnet/Testnet
- Ensure network dropdown matches your wallet's network
- Devnet tokens have no real value
- Balances will differ from mainnet

#### Mainnet
- Verify you have sufficient tokens for trading
- Double-check token addresses before trading

### Performance Tips
- Use a stable internet connection
- Close unnecessary browser tabs
- Ensure your computer has adequate resources
- Restart the application if performance degrades

### Checking Application Status
1. Open browser developer tools (F12)
2. Check the Console tab for error messages
3. Look for API connectivity issues
4. Report specific error messages when seeking support

---

## Safety and Security

### Simulation Mode
⚠️ **IMPORTANT**: This application operates in SIMULATION MODE ONLY
- No real transactions are executed
- No actual tokens are bought or sold
- The application only simulates trading behavior
- Your actual wallet funds remain completely secure

### Risk Disclaimer
- Trading involves risk of loss
- Past performance doesn't guarantee future results  
- Only trade tokens you can afford to lose
- Verify all settings before starting trading
- Monitor your bot regularly

### Privacy Notice
- No personal information is collected
- No wallet data is stored externally
- Private keys never leave Phantom wallet
- All data remains local to your browser

### Best Practices
1. **Test First**: Use Devnet/Testnet before mainnet
2. **Start Small**: Begin with small trade amounts
3. **Monitor Regularly**: Check your bot's activity
4. **Secure Access**: Keep your computer secure
5. **Backup**: Maintain separate wallet backups

### Support Information
If you encounter issues:
1. Check the Troubleshooting section first
2. Verify all settings and connections
3. Note any error messages from browser console
4. Contact support with specific details