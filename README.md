# Multi-User Solana Trading Bot

A comprehensive multi-user Solana trading bot with wallet management and automated trading capabilities.

## Features

- **Multi-User Support**: Each user gets their own Solana wallet and trading instance
- **Email OTP Verification**: Secure registration with email verification
- **Wallet Management**: Add and withdraw funds from user wallets
- **Automated Trading**: Advanced trading bot with configurable parameters
- **Dark Theme UI**: Modern, responsive dark-themed interface
- **Secure Storage**: Encrypted private key storage

## Prerequisites

- Python 3.8+
- Solana account with some SOL for transaction fees
- Jupiter API key
- Gmail account with app password for email OTP
- Helius API key (optional but recommended)

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
```bash
cp .env.example .env
```

5. Edit the `.env` file with your API keys and configuration.

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Flask configuration
SECRET_KEY=your-secret-key-change-this-in-production

# Jupiter API
JUPITER_API_KEY=your-jupiter-api-key

# Helius API (optional but recommended for better RPC performance)
HELIUS_API_KEY=your-helius-api-key

# Gmail SMTP for sending OTP emails
GMAIL_EMAIL=your-gmail@gmail.com
GMAIL_APP_PASSWORD=your-gmail-app-password

# Encryption key for storing private keys securely
ENCRYPTION_KEY=your-encryption-key-generated-using-python-cryptography
```

To generate an encryption key:
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())
```

## Usage

1. Start the application:
```bash
python app/main.py
```

2. Open your browser and go to `http://localhost:5000`

3. Register a new account using your email address

4. Verify your email using the OTP sent to your inbox

5. Start trading with your personal wallet

## Architecture

- **User Model**: Handles user authentication and registration
- **Wallet Model**: Manages Solana wallets for each user
- **Trading Bot Model**: Manages trading configurations per user
- **Database**: SQLite for storing user data and configurations

## Security

- Passwords are hashed using bcrypt
- Private keys are encrypted using Fernet (AES 128)
- Session management with secure Flask sessions
- Input validation and sanitization

## API Endpoints

### Authentication
- `POST /api/register` - Register a new user
- `POST /api/verify-otp` - Verify OTP for registration
- `POST /api/login` - Login a user
- `POST /api/logout` - Logout a user

### Wallet Management
- `GET /api/wallet-info` - Get user's wallet address
- `GET /api/wallet-balance` - Get user's wallet balance
- `POST /api/add-funds` - Add funds to user's wallet
- `POST /api/withdraw-funds` - Withdraw funds from user's wallet

### Trading
- `POST /api/start-trading` - Start trading bot
- `POST /api/stop-trading` - Stop trading bot
- `GET /api/trading-status` - Get trading status
- `GET /api/pending-approvals` - Get pending trade approvals
- `POST /api/approve-trade` - Approve a trade
- `POST /api/reject-trade` - Reject a trade
- `POST /api/get-price` - Get current token price

## Trading Parameters

- **Network**: Mainnet, Devnet, or Testnet
- **Trading Mode**: Automatic or User Approval
- **Up Percentage**: Percentage increase to trigger sell
- **Down Percentage**: Percentage decrease to trigger buy
- **Trade Amount**: Total amount to trade
- **Parts**: Number of parts to divide the trade into

## Wallet Management

Users can:
- View their wallet address and token balances
- Add funds by transferring from external wallets
- Withdraw funds to external addresses
- Monitor transaction history

## Development

To run in development mode with auto-reload:
```bash
export FLASK_ENV=development
python app/main.py
```

## Deployment

For production deployment, consider:
- Using a production WSGI server like Gunicorn
- Setting up a reverse proxy with Nginx
- Using a production database like PostgreSQL
- Implementing proper logging
- Setting up SSL certificates