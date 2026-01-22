# Multi-User Solana Trading Bot

A comprehensive multi-user Solana trading bot with wallet management, automated ladder trading, and trade history tracking.

## Features

- **Multi-User Support**: Each user gets their own Solana wallet and trading instance.
- **Email OTP Verification**: Secure registration with generic SMTP support (Gmail and others).
- **Wallet Management**: Real-time balance tracking, deposit, and withdrawal capabilities.
- **Automated Trading**: Advanced ladder trading algorithm with configurable parameters.
- **Trade History**: Comprehensive log of all trades with PnL tracking and date filtering.
- **Dark Theme UI**: Modern, responsive dark-themed interface with glassmorphism effects.
- **Secure Storage**: Encrypted private key storage using Fernet (AES-128).
- **Dynamic Pricing**: Automatically sets base trading price to current market value on start.
- **Token Support**: Supports SOL, USDC, and various SPL tokens including BONK, RAY, JUP, USDT, mSOL, stSOL, PYTH, WIF, JTO, ORCA, ETH, WBTC.
- **Withdrawal Functionality**: Secure withdrawal of SOL and SPL tokens to external addresses.
- **User Approval Mode**: Option to require manual approval for each trade in user mode.
- **Network Flexibility**: Support for mainnet, devnet, and testnet environments.

## Prerequisites

- Python 3.8+
- **MongoDB 6.0+** (Local or Atlas)
- Solana account with SOL for transaction fees.
- Jupiter API key for trading and quotes.
- SMTP account (e.g., Gmail with App Password) for sending OTP emails.
- Helius API key (optional but recommended for RPC performance).

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd solana-trading-bot
```

2. Create a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Linux/Mac
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory (see [Environment Variables](#environment-variables)).

5. Run the application:
```bash
# On Windows
python app/main.py
# Or use the batch script
run_app.bat

# On Linux/Mac
python app/main.py
```

## Environment Variables

Create a `.env` file with the following variables:

```env
# Flask configuration
SECRET_KEY=your-secret-key-change-this-in-production

# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017/trading_bot

# Jupiter API
JUPITER_API_KEY=your-jupiter-api-key

# Helius API (optional - for enhanced RPC performance)
HELIUS_API_KEY=your-helius-api-key

# SMTP Configuration for OTP Emails
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_EMAIL=your-email@gmail.com

# Encryption key for storing private keys securely
ENCRYPTION_KEY=your-encryption-key
```

> [!TIP]
> To generate a secure `ENCRYPTION_KEY`:
> ```python
> from cryptography.fernet import Fernet
> print(Fernet.generate_key().decode())
> ```

## Usage

1. **Start MongoDB**: Ensure your MongoDB service is running.
2. **Start the application**:
```bash
python app/main.py
```
3. **Access the UI**: Go to `http://localhost:5000` in your browser.
4. **Register**: Sign up with your email and verify via the OTP sent.
5. **Fund Wallet**: Deposit SOL/USDC to your generated wallet address.
6. **Configure & Start**: Set your trading parameters and click "INITIATE SEQUENCE".

## Database Setup

The application uses MongoDB for data storage with the following collections and indexes:

- **users**: Stores user information with unique email index
- **wallets**: Stores wallet information with unique public key index and user_id reference
- **trading_bots**: Stores trading bot configurations with user_id reference
- **trades**: Stores trade history with user_id and timestamp indexing

The application automatically initializes these collections and indexes when started.

## API Endpoints

### Authentication
- `POST /api/register` - Register a new user.
- `POST /api/verify-otp` - Verify OTP for registration.
- `POST /api/login` - Login a user.
- `POST /api/logout` - Logout a user.

### Wallet & Trading
- `GET /api/wallet-info` - Get user's wallet address.
- `GET /api/wallet-balance` - Get real-time wallet balances.
- `GET /api/wallet-balance/<wallet_address>` - Get wallet balance for specific address.
- `GET /api/wallet-balance/<wallet_address>/<network>` - Get wallet balance for specific address on specific network.
- `POST /api/start-trading` - Start automated ladder trading.
- `POST /api/stop-trading` - Stop trading bot.
- `GET /api/trading-status` - Get current bot status and progress.
- `POST /api/trades/history` - Get trade history for a specific date.
- `GET /api/pending-approvals` - Get pending trade approvals for user mode.
- `POST /api/approve-trade` - Approve a pending trade.
- `POST /api/reject-trade` - Reject a pending trade.
- `GET /api/deposit-address` - Get user's deposit address.
- `POST /api/withdraw-funds` - Withdraw funds to external address.

### Pricing
- `POST /api/get-price` - Get current price for a token pair using Jupiter API.

## Trading Algorithm

The trading bot implements a sophisticated ladder trading algorithm with the following features:

- **Dynamic Base Price**: The base price is automatically set to the current market price when trading starts and updates after each successful transaction.
- **Buy/Sell Logic**:
  - Buy when current price ≤ base price × (1 - down_percentage/100)
  - Sell when current price ≥ base price × (1 + up_percentage/100)
- **Part-Based Trading**: The total trade amount is divided into configurable parts for ladder-style trading.
- **Laddering Mechanism**: Each successful buy creates a sell opportunity, and each successful sell creates a buy opportunity.
- **Profit Calculation**: Profit is calculated based on the difference between sell and buy prices, with transaction fees deducted.
- **Position Tracking**: Tracks the number of tokens held and average purchase price.

## Trading Parameters

- **Network**: Mainnet, Devnet, or Testnet.
- **Trading Mode**:
  - Automatic (Autonomous): Trades execute without user intervention.
  - User Approval (Manual): Requires manual approval for each trade.
- **Up Percentage**: Threshold percentage above base price for selling.
- **Down Percentage**: Threshold percentage below base price for buying.
- **Selected Token**: Token to trade (SOL, USDC, or other supported SPL tokens).
- **Trade Amount**: Total dollar value allocated for the sequence.
- **Parts**: Number of ladder rungs to divide the total amount.

## Supported Tokens

The application supports trading of the following tokens:

- **Native Tokens**: SOL
- **Wrapped Tokens**: wSOL, Wrapped Ether (Wormhole), Wrapped BTC (Wormhole)
- **Stablecoins**: USDC, USDT
- **Popular SPL Tokens**: BONK, RAY, JUP, mSOL, stSOL, PYTH, dogwifhat (WIF), JITO (JTO), ORCA
- **Custom Tokens**: Any SPL token with a valid mint address

## Security

- **Bcrypt**: For hashing user passwords.
- **Fernet (AES)**: For encrypting Solana private keys at rest.
- **Environment Isolation**: Sensitive keys managed via `.env`.
- **Session Security**: Secure Flask session management.
- **Transaction Fees**: Estimated at $0.02 per transaction for profit calculations.
- **Balance Validation**: Checks wallet balances before executing trades.

## Withdrawal Functionality

The application provides secure withdrawal capabilities:

- **SOL Withdrawals**: Transfer SOL to any external Solana address.
- **SPL Token Withdrawals**: Transfer SPL tokens to any external Solana address.
- **Automatic ATA Creation**: Creates associated token accounts when needed.
- **Fee Handling**: Ensures sufficient SOL balance for transaction fees.

## Development

```bash
# Run with auto-reload
python app/main.py
```

## Deployment

- Use **Gunicorn** or similar WSGI server for production.
- Set up **Nginx** as a reverse proxy.
- Use **SSL/TLS** certificates for all traffic.
- Ensure MongoDB is properly secured with authentication.
- Configure environment variables for production settings.
- Monitor transaction fees and adjust as needed.