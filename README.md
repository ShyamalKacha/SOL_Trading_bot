# Solana Trading Bot

A web-based automated trading bot that uses Jupiter's Quote API to execute trades based on user-defined price thresholds. The bot connects to Phantom wallet and supports trading of various Solana tokens including SOL, wSOL, and USDC.

## Features

- Connect to Phantom wallet for token management
- Set base price and percentage thresholds for automated trading
- Real-time price tracking using Jupiter API
- Automated buying when price drops below base price
- Automated selling when price exceeds upper or lower thresholds
- Transaction history logging
- Support for SOL, wSOL, and USDC tokens
- Trade simulation mode (no actual transactions executed)

## Requirements

- Python 3.7 or higher
- Phantom wallet browser extension
- Node.js (for development)

## Installation

1. Clone the repository or download the project files
2. Make sure you have Python 3.7+ installed
3. Run the application using the provided batch file:
   ```
   run_app.bat
   ```
   This will:
   - Create a virtual environment if it doesn't exist
   - Install all required dependencies
   - Start the Flask application

## Manual Installation

If you prefer to set up manually:

1. Create a virtual environment:
   ```
   python -m venv venv
   ```

2. Activate the virtual environment:
   - On Windows: `venv\Scripts\activate`
   - On macOS/Linux: `source venv/bin/activate`

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python -m app.main
   ```

## Usage

1. Open your browser and navigate to `http://localhost:5000`
2. Connect your Phantom wallet by clicking the "Connect Wallet" button
3. Select the token you want to trade from the dropdown
4. Set your base price (the price at which you want to trigger trades)
5. Set your up percentage (the percentage above base price to sell)
6. Set your down percentage (the percentage below base price to sell)
7. Set the trade amount (how much of the token to trade per transaction)
8. Click "Start Trading" to begin the automated trading

## Trading Logic

The bot follows this trading strategy:

1. If the current price is lower than the base price and the last action was not a buy, it will buy the token
2. If the current price is higher than (base price * (1 + up percentage)) OR lower than (base price * (1 - down percentage)) and the last action was not a sell, it will sell the token
3. The bot will not perform the same action consecutively (e.g., it won't buy twice in a row or sell twice in a row)

## Project Structure

```
solana-trading-bot/
│
├── app/
│   ├── __init__.py
│   ├── main.py             # Main Flask application
│   └── templates/
│       └── index.html      # Main web interface
├── app/static/
│   ├── css/
│   └── js/
├── requirements.txt        # Python dependencies
├── jupiter_api.md          # Jupiter API documentation
├── run_app.bat             # Windows batch file to run the application
├── .gitignore
└── README.md
```

## API Endpoints

- `GET /` - Main web interface
- `GET /api/wallet-balance` - Get token balances (mock implementation)
- `POST /api/get-price` - Get current price for a token pair from Jupiter API
- `POST /api/start-trading` - Start the automated trading algorithm
- `POST /api/stop-trading` - Stop the automated trading algorithm
- `GET /api/trading-status` - Get current trading status and price

## Jupiter API Integration

The bot uses Jupiter's Quote API to get real-time token prices:

- Endpoint: `https://quote-api.jup.ag/v6/quote`
- Parameters: inputMint, outputMint, amount, slippageBps
- All trades are simulated and not executed on mainnet

## Security

- All transactions are simulated (no real trades are executed)
- The application only reads wallet information and does not have permission to make transactions
- Private keys remain in the Phantom wallet and are never accessed by the application

## Limitations

- This is a simulation application; no real trades are executed
- Price updates happen every 5 seconds
- Only supports a limited set of tokens (SOL, wSOL, USDC)
- Requires an internet connection to fetch price data

## Troubleshooting

If you encounter issues:
1. Make sure your Phantom wallet is installed and updated
2. Ensure you have an active internet connection
3. Check the browser console for any JavaScript errors
4. Review the terminal output for any Python errors
5. Make sure all dependencies were installed correctly
