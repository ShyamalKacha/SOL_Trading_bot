from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import requests
import json
from dotenv import load_dotenv
import os
import sys

# Add the parent directory to sys.path to allow imports from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base58 import b58decode
# sqlite3 import removed
from datetime import datetime, timedelta
import threading
import time
import queue
import uuid
from cryptography.fernet import Fernet
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import bcrypt
import secrets

# Load environment variables
load_dotenv()

# Import Solana libraries with fallbacks
try:
    from solana.publickey import PublicKey
    from solana.rpc.api import Client
    from solana.transaction import Transaction
    from solana.keypair import Keypair
    from spl.token.constants import TOKEN_PROGRAM_ID
except ImportError:
    # For compatibility if solana library structure changes
    try:
        from solders.pubkey import Pubkey as PublicKey
        from solana.rpc.api import Client
        from solana.transaction import Transaction
        from solders.keypair import Keypair
        from spl.token.constants import TOKEN_PROGRAM_ID
    except ImportError:
        # Mock objects for testing if libraries not available
        class PublicKey:
            def __init__(self, key):
                self.key = key
        class Client:
            pass
        class Transaction:
            pass
        class Keypair:
            pass
        # Define a default TOKEN_PROGRAM_ID for fallback
        TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

# Import models
from models.user import User
from models.wallet import Wallet
from models.trading_bot import TradingBot
from models.trade import Trade
from database import init_db

app = Flask(__name__, template_folder='../templates', static_folder='../static')
CORS(app, supports_credentials=True) # Enable CORS for all routes, allowing credentials (cookies/session)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')

# Initialize database tables
init_db()

# Constants
# Using the Jupiter API endpoint for quotes (requires API key)
JUPITER_QUOTE_API = "https://api.jup.ag/swap/v1/quote"
JUPITER_SWAP_API = "https://api.jup.ag/swap/v1/swap"

# Minimum balance required for mainnet trading (initial check)
# Now used as a buffer for gas fees
MIN_MAINNET_BALANCE = 0.00005

# Mock data for demonstration
# SOL mint address
SOL_MINT = "So11111111111111111111111111111111111111112"
# wSOL mint address (Wrapped SOL - SPL Token)
# Using the same address as SOL for swap purposes since they are functionally equivalent
WSOL_MINT = "So11111111111111111111111111111111111111112"
# For UI purposes, we'll treat them as separate options but use same address for swaps
# USDC mint address (using the correct mainnet USDC mint)
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

MOCK_TOKENS = [
    {"symbol": "SOL", "mint": SOL_MINT, "name": "Solana"},
    {"symbol": "wSOL", "mint": WSOL_MINT, "name": "Wrapped Solana"},
    {"symbol": "USDC", "mint": USDC_MINT, "name": "USD Coin"},
]

# Token information mapping - expanded with common SPL tokens
TOKEN_INFO = {
    SOL_MINT: {"symbol": "SOL", "name": "Solana"},
    # SOL and wSOL have the same mint address but may be treated differently in UI
    # For display purposes, we'll treat them the same since they have the same underlying value
    "So11111111111111111111111111111111111111112": {"symbol": "SOL", "name": "Solana"},  # Standard SOL address
    USDC_MINT: {"symbol": "USDC", "name": "USD Coin"},
    # Additional common SPL tokens
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": {"symbol": "BONK", "name": "Bonk"},
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R": {"symbol": "RAY", "name": "Raydium"},
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": {"symbol": "JUP", "name": "Jupiter"},
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": {"symbol": "USDT", "name": "Tether USD"},
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So": {"symbol": "mSOL", "name": "Marinade Staked SOL"},
    "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj": {"symbol": "stSOL", "name": "Lido Staked SOL"},
    "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3": {"symbol": "PYTH", "name": "Pyth Network"},
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm": {"symbol": "WIF", "name": "dogwifhat"},
    "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL": {"symbol": "JTO", "name": "Jito"},
    "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE": {"symbol": "ORCA", "name": "Orca"},
    "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs": {"symbol": "ETH", "name": "Wrapped Ether (Wormhole)"},
    "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh": {"symbol": "WBTC", "name": "Wrapped BTC (Wormhole)"},
}

# Global dictionary to store trading state for each user
user_trading_states = {}

# Global dictionary for pending trade approvals (per user)
user_pending_approvals = {}
user_approvals_locks = {}
user_approvals_queues = {}

def get_user_trading_state(user_id):
    """Get or create trading state for a user"""
    if user_id not in user_trading_states:
        user_trading_states[user_id] = {
            "is_running": False,
            "last_action": None,  # 'buy' or 'sell'
            "current_price": 0,
            "dynamic_base_price": None,
            "total_profit": 0,  # Track total profit
            "position": 0,  # Track number of tokens held
            "avg_purchase_price": 0,  # Track average purchase price
            "parts": 0,  # Total number of parts
            "part_size": 0,  # Size of each part
            "remaining_parts": 0,  # Number of remaining parts to sell
            "transaction_history": [],
            "buy_parts": [],  # Array to track buy parts
            "sell_parts": [],  # Array to track sell parts
             # ✅ ADD THESE FIELDS
            "up_percentage": None,        # ◄── NEW
            "down_percentage": None,      # ◄── NEW
            "selected_token": None,       # ◄── NEW
            "trade_amount": None,         # ◄── NEW
            "network": None,              # ◄── NEW
            "trading_mode": None,         # ◄── NEW
        }
    return user_trading_states[user_id]

def get_user_pending_approvals(user_id):
    """Get or create pending approvals for a user"""
    if user_id not in user_pending_approvals:
        user_pending_approvals[user_id] = []
    if user_id not in user_approvals_locks:
        user_approvals_locks[user_id] = threading.Lock()
    if user_id not in user_approvals_queues:
        user_approvals_queues[user_id] = queue.Queue()
    return user_pending_approvals[user_id], user_approvals_locks[user_id], user_approvals_queues[user_id]

def send_otp_email(email, otp):
    """Send OTP to user's email using configurable SMTP"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        # Get SMTP configuration from environment
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME') or os.getenv('GMAIL_EMAIL')  # Fallback to GMAIL_EMAIL
        smtp_password = os.getenv('SMTP_PASSWORD') or os.getenv('GMAIL_APP_PASSWORD')  # Fallback to GMAIL_APP_PASSWORD
        sender_email = os.getenv('SENDER_EMAIL') or os.getenv('GMAIL_EMAIL')  # Fallback to GMAIL_EMAIL

        # Check if we have the required environment variables
        if not smtp_username or not smtp_password or not sender_email:
            print("SMTP configuration not complete in environment")
            return False

        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = "Your OTP for Registration"

        # Create HTML content
        html_content = f"""
        <html>
        <body>
            <h2>Solana Trading Bot Registration</h2>
            <p>Your OTP for registration is: <strong>{otp}</strong></p>
            <p>This OTP will expire in 10 minutes.</p>
            <p>If you didn't request this, please ignore this email.</p>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, 'html'))

        # Connect to SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable encryption
        server.login(smtp_username, smtp_password)

        # Send email
        text = msg.as_string()
        server.sendmail(sender_email, email, text)
        server.quit()

        print(f"OTP sent successfully to {email}")
        return True

    except Exception as e:
        print(f"Error sending OTP: {e}")
        return False

def generate_otp():
    """Generate a 6-digit OTP"""
    return str(secrets.randbelow(900000) + 100000)  # Generates a 6-digit number

def require_login(f):
    """Decorator to require user login"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "Authentication required"}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Routes for authentication - CHANGED FOR REACT
@app.route('/api/check-auth')
def check_auth():
    """Check if user is authenticated and return user info"""
    if 'user_id' in session:
        return jsonify({"authenticated": True, "user_id": session['user_id']})
    return jsonify({"authenticated": False}), 401

@app.route('/')
def index():
    return jsonify({"message": "Backend is running. Please access via frontend."})

@app.route('/login')
def login():
    return jsonify({"message": "Please use POST /api/login"})

@app.route('/register')
def register():
    return jsonify({"message": "Please use POST /api/register"})

@app.route('/dashboard')
@require_login
def dashboard():
    helius_api_key = os.getenv('HELIUS_API_KEY', '')
    return jsonify({
        "message": "Welcome to dashboard API", 
        "helius_api_key": helius_api_key,
        "user_id": session['user_id']
    })

@app.route('/api/register', methods=['POST'])
def api_register():
    """Register a new user"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"}), 400
    
    # Check if user already exists
    existing_user = User.find_by_email(email)
    if existing_user:
        return jsonify({"success": False, "message": "Email already registered"}), 400
    
    # Create new user
    user = User(email=email)
    user.set_password(password)
    user.save()
    
    # Generate OTP
    otp = generate_otp()
    otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    
    # Store OTP in database
    User.set_otp_secret(email, otp, otp_expiry)
    
    # Send OTP via email
    if send_otp_email(email, otp):
        return jsonify({"success": True, "message": "Registration successful. Please check your email for OTP."})
    else:
        return jsonify({"success": False, "message": "Registration successful but failed to send OTP. Please contact support."}), 500

@app.route('/api/verify-otp', methods=['POST'])
def api_verify_otp():
    """Verify OTP for registration"""
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    
    if not email or not otp:
        return jsonify({"success": False, "message": "Email and OTP are required"}), 400
    
    # Verify OTP
    if User.verify_otp(email, otp):
        # Create wallet for the user
        user = User.find_by_email(email)
        if user:
            wallet = Wallet.create_wallet_for_user(user.id)
            # Create trading bot for the user
            TradingBot.create_bot_for_user(user.id)
            return jsonify({"success": True, "message": "OTP verified. Account created successfully."})
        else:
            return jsonify({"success": False, "message": "User not found"}), 400
    else:
        return jsonify({"success": False, "message": "Invalid or expired OTP"}), 400

@app.route('/api/login', methods=['POST'])
def api_login():
    """Login a user"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"}), 400
    
    user = User.find_by_email(email)
    if user and user.check_password(password):
        session['user_id'] = user.id
        return jsonify({"success": True, "message": "Login successful"})
    else:
        return jsonify({"success": False, "message": "Invalid email or password"}), 401

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Logout a user"""
    session.pop('user_id', None)
    return jsonify({"success": True, "message": "Logged out successfully"})

# API routes for wallet and trading functionality
@app.route('/api/wallet-info')
@require_login
def get_wallet_info():
    """Get wallet address for the logged-in user"""
    try:
        user_id = session['user_id']
        wallet = Wallet.find_by_user_id(user_id)
        
        if not wallet:
            return jsonify({
                "success": False,
                "message": "Wallet not found for user",
                "wallet_address": None
            })

        return jsonify({
            "success": True,
            "wallet_address": wallet.public_key
        })
    except Exception as e:
        print(f"Error in get_wallet_info: {e}")
        return jsonify({
            "success": False,
            "message": f"Error getting wallet info: {str(e)}",
            "wallet_address": None
        })

@app.route('/api/wallet-balance')
@require_login
def get_wallet_balance_default():
    """Get wallet balance for the logged-in user"""
    try:
        user_id = session['user_id']
        wallet = Wallet.find_by_user_id(user_id)

        if not wallet:
            return jsonify({
                "success": False,
                "message": "Wallet not found for user",
                "balances": []
            })

        # GET NETWORK FROM QUERY PARAMETER (default to mainnet)
        network = request.args.get('network', 'mainnet').lower()
        
        # Validate network
        if network not in ['mainnet', 'devnet', 'testnet']:
            network = 'mainnet'

        # Fetch real balance from Solana blockchain with specified network
        response = get_wallet_balance(wallet.public_key, network)
        
        # Update the wallet's balance in the database
        if isinstance(response, dict) and response.get("success"):
            wallet.update_balance(response.get("balances", []))
        
        return jsonify(response)
    except Exception as e:
        print(f"Error in get_wallet_balance_default: {e}")
        return jsonify({
            "success": False,
            "message": f"Error getting wallet balance: {str(e)}",
            "balances": []
        })
    """Get wallet balance for the logged-in user"""
    try:
        user_id = session['user_id']
        wallet = Wallet.find_by_user_id(user_id)

        if not wallet:
            return jsonify({
                "success": False,
                "message": "Wallet not found for user",
                "balances": []
            })

        # Fetch real balance from Solana blockchain
        response = get_wallet_balance(wallet.public_key, "mainnet")
        # Update the wallet's balance in the database
        # Response is now a dict, not a Response object
        if isinstance(response, dict) and response.get("success"):
            wallet.update_balance(response.get("balances", []))
        return response
    except Exception as e:
        print(f"Error in get_wallet_balance_default: {e}")
        return jsonify({
            "success": False,
            "message": f"Error getting wallet balance: {str(e)}",
            "balances": []
        })

@app.route('/api/wallet-balance/<wallet_address>')
@app.route('/api/wallet-balance/<wallet_address>/<network>')
def get_wallet_balance(wallet_address, network="mainnet"):
    """Function to get real wallet token balances from Solana blockchain"""
    try:
        # Validate wallet address format (basic check)
        if len(wallet_address) < 32 or len(wallet_address) < 32:
            return {
                "success": False,
                "message": "Invalid wallet address format",
                "balances": []
            }

        # Determine the RPC URL based on the network and check for Helius API key
        helius_api_key = os.getenv('HELIUS_API_KEY')

        if network.lower() == "devnet":
            if helius_api_key:
                rpc_url = f"https://devnet.helius-rpc.com/?api-key={helius_api_key}"
            else:
                rpc_url = "https://api.devnet.solana.com"
        elif network.lower() == "testnet":
            # if helius_api_key:
            #     rpc_url = f"https://testnet.helius-rpc.com/?api-key={helius_api_key}"
            # else:
                rpc_url = "https://api.testnet.solana.com"
        else:  # default to mainnet
            if helius_api_key:
                rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_api_key}"
            else:
                rpc_url = "https://api.mainnet-beta.solana.com"

        # For now, we'll use the RPC URL directly
        # The original solana_client approach may be better for some operations
        import json

        headers = {
            "Content-Type": "application/json"
        }

        # Get token accounts
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                wallet_address,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        }

        response = requests.post(rpc_url, headers=headers, data=json.dumps(payload))
        result = response.json()

        balances = []

        # Check if we got a proper response
        if 'result' in result and 'value' in result['result']:
            for token_account in result['result']['value']:
                account_info = token_account['account']['data']['parsed']['info']
                mint = account_info['mint']
                amount = float(account_info['tokenAmount']['uiAmount'])

                # Only add if amount is greater than 0 to avoid showing zero balances
                if amount > 0:
                    # Get token info from Jupiter or a token list
                    token_symbol = TOKEN_INFO.get(mint, {}).get("symbol", mint[:8] + "...")
                    token_name = TOKEN_INFO.get(mint, {}).get("name", "Unknown Token")

                    balances.append({
                        "token": token_symbol,
                        "name": token_name,
                        "balance": amount,
                        "mint": mint,
                        "decimals": account_info['tokenAmount']['decimals']
                    })
        elif 'error' in result:
            print(f"Error from RPC for token accounts: {result['error']}")

        # Add SOL separately (everyone has SOL account, even if 0 balance)
        sol_payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "getBalance",
            "params": [wallet_address]
        }

        sol_response = requests.post(rpc_url, headers=headers, data=json.dumps(sol_payload))
        sol_result = sol_response.json()

        if 'result' in sol_result and 'value' in sol_result['result']:
            sol_amount = sol_result['result']['value'] / 10**9  # Convert lamports to SOL
            # Add SOL to balances if there's a balance
            if sol_amount > 0:
                balances.append({
                    "token": "SOL",
                    "name": "Solana",
                    "balance": sol_amount,
                    "mint": "So11111111111111111111111111111111111111112",
                    "decimals": 9
                })
        else:
            print(f"SOL balance query failed for {wallet_address}: {sol_result}")

        return {
            "success": True,
            "balances": balances
        }

    except Exception as e:
        print(f"Error in get_wallet_balance: {e}")
        return {
            "success": False,
            "message": f"Error connecting to wallet: {str(e)}",
            "balances": []
        }

@app.route('/api/get-price', methods=['POST'])
def get_price():
    """Get current price for a token pair using Jupiter API"""
    data = request.get_json()
    input_mint = data.get('inputMint', 'So11111111111111111111111111111111111111112')  # SOL
    output_mint = data.get('outputMint', 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')  # USDC
    amount = data.get('amount', 1000000000)  # Default to 1 SOL (in lamports)

    # Get Jupiter API key from environment
    jupiter_api_key = os.getenv('JUPITER_API_KEY')

    headers = {
        "x-api-key": jupiter_api_key
    }

    params = {
        'inputMint': input_mint,
        'outputMint': output_mint,
        'amount': str(amount),  # Convert to string as required
        'swapMode': 'ExactIn',
        'slippageBps': 50,
        'restrictIntermediateTokens': 'true',
        'maxAccounts': 64,
        'instructionVersion': 'V1'
    }

    try:
        response = requests.get(JUPITER_QUOTE_API, params=params, headers=headers)
        if response.status_code == 200:
            quote_data = response.json()
            # Check if quote contains necessary data
            if 'outAmount' in quote_data and 'inAmount' in quote_data:
                out_amount = int(quote_data['outAmount'])
                in_amount = int(quote_data['inAmount'])

                # Price calculation with proper decimal adjustment
                if in_amount == 0:
                    return jsonify({"price": 0.0, "success": False, "message": "Input amount is zero"})

                # SOL (9 decimals) → USDC (6 decimals) price calculation
                price = (out_amount / 10**6) / (in_amount / 10**9)

                return jsonify({"price": price, "success": True})
            else:
                # If essential data is missing, return error
                return jsonify({"price": 0.0, "success": False, "message": f"Quote data missing: {quote_data}"})
        else:
            # If the API returns an error status, try to provide more useful error info
            error_text = response.text if response.text else f"HTTP {response.status_code}"
            return jsonify({"price": 0.0, "success": False, "message": f"API Error: {response.status_code} - {error_text}"})
    except Exception as e:
        print(f"Error fetching price: {e}")
        # On error, return a default price and indicate failure
        return jsonify({"price": 0.0, "success": False, "message": str(e)})

@app.route('/api/start-trading', methods=['POST'])
@require_login
def start_trading():
    """Start the trading algorithm for the logged-in user"""
    user_id = session['user_id']
    trading_state = get_user_trading_state(user_id)
    
    data = request.get_json()

    # Extract trade amount and parts early to calculate part amount
    try:
        trade_amount = float(data.get('tradeAmount', 0))
        parts = int(data.get('parts', 1)) 
        if parts <= 0: parts = 1
        part_amount = trade_amount / parts
    except (ValueError, TypeError):
        part_amount = 0
        
    # Extract network early for validation
    network = data.get('network', 'mainnet').lower()

    # Check wallet balance if on mainnet to prevent trading with insufficient funds
    if network == 'mainnet':
        wallet = Wallet.find_by_user_id(user_id)
        if not wallet:
            return jsonify({"error": "Wallet not found. Please setup your wallet first."}), 400
            
        # Get current balance
        balance_response = get_wallet_balance(wallet.public_key, network)
        
        if not balance_response.get('success'):
            return jsonify({"error": f"Failed to check wallet balance: {balance_response.get('message')}"}), 400
            
        # Find SOL balance
        sol_balance = 0
        for token in balance_response.get('balances', []):
            if token['token'] == 'SOL':
                sol_balance = token['balance']
                break
                
        if sol_balance < (part_amount + MIN_MAINNET_BALANCE):
            return jsonify({
                "error": f"Insufficient SOL balance. Required per part: {part_amount:.4f} SOL + {MIN_MAINNET_BALANCE} SOL (fees) = {(part_amount + MIN_MAINNET_BALANCE):.4f} SOL. Available: {sol_balance:.4f} SOL."
            }), 400

    required_fields = ['upPercentage', 'downPercentage', 'selectedToken', 'tradeAmount', 'parts']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # We no longer need basePrice from the form - we'll get current market price and use that as base
    up_percentage = float(data['upPercentage'])
    down_percentage = float(data['downPercentage'])
    selected_token = data['selectedToken']
    trade_amount = float(data['tradeAmount'])
    parts = int(data['parts'])

    # Get optional parameters for network and trading mode
    network = data.get('network', 'mainnet').lower()
    trading_mode = data.get('tradingMode', 'automatic').lower()

    # Validate that trade amount and parts are positive
    if trade_amount <= 0:
        return jsonify({"error": "Trade amount must be greater than 0"}), 400
    if parts <= 0:
        return jsonify({"error": "Parts must be greater than 0"}), 400
    if trading_mode not in ['user', 'automatic']:
        return jsonify({"error": "Trading mode must be 'user' or 'automatic'"}), 400
    if network not in ['mainnet', 'devnet', 'testnet']:
        return jsonify({"error": "Network must be 'mainnet', 'devnet', or 'testnet'"}), 400

    # Stop any existing trading thread for this user
    trading_state['is_running'] = False

    # Start new trading thread - the algorithm will fetch current price and use it as base
    trading_thread = threading.Thread(
        target=trading_algorithm,
        args=(user_id, 0, up_percentage, down_percentage, selected_token, trade_amount, parts, network, trading_mode)  # Pass 0 as placeholder for base_price
    )
    trading_thread.daemon = True
    trading_thread.start()

    return jsonify({"message": "Trading started"})

@app.route('/api/stop-trading', methods=['POST'])
@require_login
def stop_trading():
    """Stop the trading algorithm for the logged-in user"""
    user_id = session['user_id']
    trading_state = get_user_trading_state(user_id)
    trading_state['is_running'] = False
    return jsonify({"message": "Trading stopped"})

@app.route('/api/trading-status')
@require_login
def get_trading_status():
    """Get current trading status for the logged-in user"""
    user_id = session['user_id']
    trading_state = get_user_trading_state(user_id)
    
    # Ensure dynamic base price is present in response
    status = trading_state.copy()
    # If dynamic_base_price is not set, default to the original base price concept
    if 'dynamic_base_price' not in status or status['dynamic_base_price'] is None:
        status['dynamic_base_price'] = status.get('original_base_price', 0)

    # Add buy and sell parts counts to the status
    status['buy_parts_count'] = len(status.get('buy_parts', []))
    status['sell_parts_count'] = len(status.get('sell_parts', []))

    # ✅ ADD THESE LINES - Include configuration in response
    # Ensure these fields exist even if bot hasn't been started yet
    status['up_percentage'] = status.get('up_percentage', None)          # ◄── NEW
    status['down_percentage'] = status.get('down_percentage', None)      # ◄── NEW
    status['selected_token'] = status.get('selected_token', None)        # ◄── NEW
    status['trade_amount'] = status.get('trade_amount', None)            # ◄── NEW
    status['network'] = status.get('network', None)                      # ◄── NEW
    status['trading_mode'] = status.get('trading_mode', None)            # ◄── NEW


    return jsonify(status)

@app.route('/api/pending-approvals')
@require_login
def get_pending_approvals():
    """Get pending trade approvals for the logged-in user"""
    user_id = session['user_id']
    try:
        approvals, lock, queue = get_user_pending_approvals(user_id)
        with lock:
            # Return a copy of the list to avoid race conditions
            user_approvals = [approval.copy() for approval in approvals if approval.get('result') == 'pending']
        return jsonify({"approvals": user_approvals})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/approve-trade', methods=['POST'])
@require_login
def approve_trade():
    """Approve a pending trade for the logged-in user"""
    user_id = session['user_id']
    try:
        data = request.get_json()
        trade_id = data.get('trade_id')

        approvals, lock, queue_obj = get_user_pending_approvals(user_id)
        
        # Update both the list and queue
        with lock:
            # Update in the list
            for approval in approvals:
                if approval['id'] == trade_id:
                    approval['approved'] = True
                    approval['result'] = 'approved'
                    break

        # Also put approval result in the queue for the trading algorithm
        approval_result = {
            'id': trade_id,
            'approved': True,
            'result': 'approved'
        }
        queue_obj.put(approval_result)

        return jsonify({"success": True, "message": "Trade approved"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reject-trade', methods=['POST'])
@require_login
def reject_trade():
    """Reject a pending trade for the logged-in user"""
    user_id = session['user_id']
    try:
        data = request.get_json()
        trade_id = data.get('trade_id')

        approvals, lock, queue_obj = get_user_pending_approvals(user_id)
        
        # Update both the list and queue
        with lock:
            # Update in the list
            for approval in approvals:
                if approval['id'] == trade_id:
                    approval['approved'] = False
                    approval['result'] = 'rejected'
                    break

        # Also put rejection result in the queue for the trading algorithm
        approval_result = {
            'id': trade_id,
            'approved': False,
            'result': 'rejected'
        }
        queue_obj.put(approval_result)

        return jsonify({"success": True, "message": "Trade rejected"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/trade-history')
@require_login
def trade_history_page():
    """Render the trade history page - DEPRECATED for API"""
    return jsonify({"message": "Use /api/trades/history for history data"})

@app.route('/api/trades/history', methods=['POST'])
@require_login
def get_trade_history():
    """Get trade history for a specific date"""
    user_id = session['user_id']
    data = request.get_json()
    date_str = data.get('date') # YYYY-MM-DD
    
    network = data.get('network')
    
    if not date_str:
        return jsonify({"success": False, "message": "Date is required"}), 400
        
    try:
        trades = Trade.find_by_user_and_date(user_id, date_str, network)
        
        # Calculate totals
        total_pnl = 0
        trade_list = []
        
        for trade in trades:
            if trade.pnl is not None:
                total_pnl += trade.pnl
                
            trade_list.append({
                "timestamp": trade.timestamp,
                "action": trade.action,
                "token_symbol": trade.token_symbol,
                "price": trade.price,
                "amount": trade.amount,
                "pnl": trade.pnl,
                "status": trade.status
            })
            
        return jsonify({
            "success": True,
            "trades": trade_list,
            "total_pnl": total_pnl,
            "count": len(trade_list)
        })
    except Exception as e:
        print(f"Error fetching trade history: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/orders', methods=['GET'])
@require_login
def get_orders():
    """Get paginated orders for the logged-in user"""
    user_id = session['user_id']
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 15))
    network = request.args.get('network')
    
    try:
        trades, total_count = Trade.find_by_user(user_id, page, per_page, network)
        
        trade_list = []
        for trade in trades:
            trade_list.append({
                "timestamp": trade.timestamp,
                "action": trade.action,
                "token_symbol": trade.token_symbol,
                "price": trade.price,
                "amount": trade.amount,
                "pnl": trade.pnl,
                "status": trade.status,
                "network": trade.network
            })
            
        import math
        total_pages = math.ceil(total_count / per_page)
        
        return jsonify({
            "success": True,
            "orders": trade_list,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_items": total_count,
                "per_page": per_page
            }
        })
    except Exception as e:
        print(f"Error fetching orders: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

def trading_algorithm(user_id, base_price, up_percentage, down_percentage, selected_token, trade_amount, parts, network="mainnet", trading_mode="automatic"):
    """Main trading algorithm with correct laddering logic - each transaction updates the base price"""
    # Ensure application context is active for this thread
    app.app_context().push()

    trading_state = get_user_trading_state(user_id)
    trading_state['is_running'] = True

    # ✅ ADD THESE LINES - Store configuration in state
    trading_state['up_percentage'] = up_percentage          # ◄── NEW
    trading_state['down_percentage'] = down_percentage      # ◄── NEW
    trading_state['selected_token'] = selected_token        # ◄── NEW
    trading_state['trade_amount'] = trade_amount            # ◄── NEW
    trading_state['network'] = network                      # ◄── NEW (already exists actually)
    trading_state['trading_mode'] = trading_mode            # ◄── NEW (already exists actually)
    

    trading_state['last_action'] = None
    trading_state['total_profit'] = 0  # Track total profit
    trading_state['trade_count'] = 0   # Track number of trades for auto-refresh
    trading_state['position'] = 0  # Track number of tokens held
    trading_state['avg_purchase_price'] = 0  # Track average purchase price

    # Calculate amount per part
    part_size = trade_amount / parts
    trading_state['parts'] = parts
    trading_state['part_size'] = part_size

    # Initialize buy and sell arrays with the specified number of parts
    # Initially, both arrays have all parts (ready for either buy or sell)
    trading_state['buy_parts'] = list(range(parts))  # All parts available for buying initially
    trading_state['sell_parts'] = list(range(parts))  # All parts available for selling initially

    # RESET transaction history for the new session (Graph will show only this session)
    trading_state['transaction_history'] = []

    # Store trading mode and network
    trading_state['trading_mode'] = trading_mode
    trading_state['network'] = network

    # Fetch initial price when starting and update base_price to current market price
    try:
        # Determine the output mint based on the selected token for initial price
        if selected_token == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v":  # USDC
            output_mint = selected_token
            input_mint = "So11111111111111111111111111111111111111112"  # SOL
        elif selected_token == "So11111111111111111111111111111111111111112":  # SOL or wSOL
            input_mint = "So11111111111111111111111111111111111111112"  # SOL
            output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
        else:
            input_mint = selected_token
            output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC

        initial_price_response = get_jupiter_price_direct(input_mint, output_mint, 1000000000)
        if initial_price_response["success"]:
            initial_current_price = initial_price_response["price"]
            # Set the base price to current market price when starting
            trading_state['base_price'] = initial_current_price
            trading_state['current_price'] = initial_current_price
            print(f"Set base price to initial current market price: {initial_current_price}")
        else:
            # If initial price fetch fails, use a default value
            default_price = 100  # Default fallback
            trading_state['base_price'] = default_price
            trading_state['current_price'] = default_price
            print(f"Using default base price: {default_price}")
    except Exception as e:
        print(f"Error getting initial price: {e}")
        default_price = 100  # Default fallback
        trading_state['base_price'] = default_price
        trading_state['current_price'] = default_price

    while trading_state['is_running']:
        try:
            # Get current price from Jupiter API
            # Determine the output mint based on the selected token
            if selected_token == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v":  # USDC
                output_mint = selected_token
                input_mint = "So11111111111111111111111111111111111111112"  # SOL (to get USDC price in SOL)
            elif selected_token == "So11111111111111111111111111111111111111112":  # SOL/wSOL same mint
                input_mint = "So11111111111111111111111111111111111111112"  # SOL/wSOL
                output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
            # For any other token, try to get price in USDC first
            else:
                input_mint = selected_token
                output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC

            # Get price from Jupiter API directly without using request context
            # Call the price API using direct Jupiter API call instead of internal Flask call
            price_response = get_jupiter_price_direct(input_mint, output_mint, 1000000000)

            current_price = None

            if price_response["success"]:
                current_price = price_response["price"]
                trading_state['current_price'] = current_price
                # Update the dynamic base price in the trading state (for UI display)
                trading_state['dynamic_base_price'] = trading_state['base_price']  # Keep this for UI display
                print(f"Got price: {current_price} for token {selected_token}, base price: {trading_state['base_price']}")
            else:
                print(f"Failed to get price for main pair: {price_response.get('message', 'Unknown error')}")

                # For tokens that don't have price data in Jupiter,
                # we need to handle this case properly. We can either:
                # 1. Skip this iteration and wait for price availability
                # Since we can't trade what we can't price, we'll log the issue and continue
                print(f"No price available for token: {selected_token}, skipping this iteration")
                # Use previous price if available, otherwise skip
                if trading_state['current_price'] is not None:
                    current_price = trading_state['current_price']  # Keep previous price
                else:
                    time.sleep(5)  # Wait before next iteration
                    continue  # Skip to the next iteration if no previous price

            # If we have a valid price (not 0 or None), proceed with trading logic
            if current_price is None or current_price <= 0:
                time.sleep(5)  # Wait before next iteration
                continue  # Skip trading logic if price is invalid

            # Get current base price for comparison
            current_base_price = trading_state['base_price']

            # Calculate thresholds based on the current base price
            sell_threshold = current_base_price * (1 + up_percentage / 100)
            buy_threshold = current_base_price * (1 - down_percentage / 100)

            # We can buy if there are buy opportunities available (buy_parts > 0)
            # We can sell if there are sell opportunities available (sell_parts > 0)
            should_buy = current_price <= buy_threshold and len(trading_state['buy_parts']) > 0
            should_sell = current_price >= sell_threshold and len(trading_state['sell_parts']) > 0

            # Execute buy/sell based on conditions - note that we can switch between buy and sell at any time
            if should_buy:
                # BUY operation
                transaction_successful = False

                # Execute real transaction if on mainnet, otherwise simulate
                if network.lower() == "mainnet":
                    # Check trading mode
                    if trading_mode == "user":
                        # In user mode, we need to wait for user confirmation
                        print(f"[USER MODE] Buy intent: {part_size} of {get_token_symbol(selected_token)} at ${current_price}")

                        # Create a trade approval request
                        trade_id = str(uuid.uuid4())
                        approval_request = {
                            'id': trade_id,
                            'action': 'buy',
                            'amount': part_size,
                            'token': get_token_symbol(selected_token),
                            'price': current_price,
                            'timestamp': datetime.now().isoformat(),
                            'approved': None,  # None means pending
                            'result': 'pending'
                        }

                        # Add to both the list (for frontend) and queue (for trading algorithm)
                        approvals, lock, queue_obj = get_user_pending_approvals(user_id)
                        with lock:
                            approvals.append(approval_request)

                        # Wait for user approval with timeout
                        approval_timeout = 30  # 30 seconds timeout
                        start_time = time.time()
                        approved = False

                        while time.time() - start_time < approval_timeout and not approved:
                            # Check if this trade has been approved/rejected from the queue
                            try:
                                check_approval = queue_obj.get_nowait()
                                if check_approval['id'] == trade_id:
                                    if check_approval['result'] == 'approved':
                                        approved = True
                                        transaction_result = execute_buy_transaction(user_id, current_price, selected_token, part_size, network)
                                        transaction_successful = transaction_result["success"]
                                    elif check_approval['result'] == 'rejected':
                                        transaction_successful = False
                                        print(f"[USER MODE] User rejected buy intent for {part_size} of {get_token_symbol(selected_token)} at ${current_price}")
                            except queue.Empty:
                                pass

                            if not approved:
                                time.sleep(0.5)  # Check more frequently

                        if not approved:
                            # Timeout - reject the trade
                            transaction_successful = False
                            print(f"[USER MODE] Timeout waiting for approval for buy intent")
                    else:  # automatic mode
                        transaction_result = execute_buy_transaction(user_id, current_price, selected_token, part_size, network)
                        transaction_successful = transaction_result["success"]
                else:
                    # For devnet/testnet, just simulate
                    simulate_buy(current_price, selected_token, part_size)
                    transaction_successful = True  # Simulation is always "successful"

                if transaction_successful:
                    # Only update state if transaction was successful
                    trading_state['last_action'] = 'buy'

                    # Record the number of buy operations completed before modifying arrays
                    buy_operations_completed = parts - len(trading_state['buy_parts'])

                    # When buying: reduce buy-parts by 1 (use a buy opportunity), increase sell-parts by 1 (create a sell opportunity)
                    if len(trading_state['buy_parts']) > 0:
                        # Remove a part from buy array (use up a buy opportunity)
                        trading_state['buy_parts'].pop()  # Remove from buy array
                        # Add a part to sell array (create a new sell opportunity)
                        if len(trading_state['sell_parts']) < parts:
                            trading_state['sell_parts'].append(len(trading_state['sell_parts']))  # Add to sell array

                    # Update base price to execution price (only on successful transaction)
                    trading_state['base_price'] = current_price

                    # Update position and average purchase price
                    old_position_value = trading_state['position'] * trading_state['avg_purchase_price']
                    new_purchase_value = part_size * current_price
                    trading_state['position'] += part_size
                    if trading_state['position'] > 0:
                        trading_state['avg_purchase_price'] = (old_position_value + new_purchase_value) / trading_state['position']

                    print(f"[TRADING] BUY: Used buy opportunity. Remaining buy opportunities: {len(trading_state['buy_parts'])}, Remaining sell opportunities: {len(trading_state['sell_parts'])} at {current_price}. New base price: {trading_state['base_price']}")

                    # Record transaction
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    tx_record = {
                        'timestamp': timestamp,
                        'action': 'buy',
                        'token': selected_token,
                        'token_symbol': get_token_symbol(selected_token),
                        'price': current_price,
                        'amount': part_size,
                        'base_price_at_execution': current_base_price,
                        'pnl': None,  # No P&L for buy transactions
                        'total_parts': parts,
                        'part_number': buy_operations_completed + 1,  # Number of buy operations completed + 1 to start from 1 (captured before array modification)
                        'execution_price': current_price,
                        'status': 'completed',  # New field to track transaction status
                        'buy_parts_count': len(trading_state['buy_parts']),
                        'sell_parts_count': len(trading_state['sell_parts']),
                        'fee_deducted': 0,  # No fee deducted for buy transactions (fee affects profit on sell)
                        'dollar_value': part_size  # Dollar value of the transaction
                    }

                    trading_state['transaction_history'].append(tx_record)

                    # Save to database
                    try:
                        trade = Trade(
                            user_id=user_id,
                            timestamp=timestamp,
                            action='buy',
                            token_symbol=get_token_symbol(selected_token),
                            token_mint=selected_token,
                            price=current_price,
                            amount=part_size,
                            pnl=None,
                            network=network,
                            status='completed'
                        )
                        trade.save()
                        # Increment trade count to trigger frontend refresh
                        trading_state['trade_count'] = trading_state.get('trade_count', 0) + 1
                        print(f"[TRADING] Saved BUY trade to database: {trade.id}")
                    except Exception as e:
                        print(f"[TRADING] Error saving trade to database: {e}")

                    # Keep only last 20 transactions
                    if len(trading_state['transaction_history']) > 20:
                        trading_state['transaction_history'] = trading_state['transaction_history'][-20:]
                else:
                    # Transaction failed, don't update base price or other state
                    print(f"[TRADING] BUY failed: Could not use buy opportunity. Remaining buy opportunities: {len(trading_state['buy_parts'])}, Remaining sell opportunities: {len(trading_state['sell_parts'])} at {current_price}. Base price unchanged: {trading_state['base_price']}")
                    # Don't move parts or update base price on failure

            elif should_sell:
                # SELL operation
                transaction_successful = False

                # Calculate the actual amount to sell based on dollar value, not fixed quantity
                # Convert the part_size (dollar value) to token amount based on current price
                actual_sell_amount = part_size / current_price  # Convert dollar value to token amount

                # Execute real transaction if on mainnet, otherwise simulate
                if network.lower() == "mainnet":
                    # Check trading mode
                    if trading_mode == "user":
                        # In user mode, we need to wait for user confirmation
                        print(f"[USER MODE] Sell intent: {actual_sell_amount} of {get_token_symbol(selected_token)} at ${current_price} (worth ${part_size:.2f})")

                        # Create a trade approval request
                        trade_id = str(uuid.uuid4())
                        approval_request = {
                            'id': trade_id,
                            'action': 'sell',
                            'amount': part_size,
                            'token': get_token_symbol(selected_token),
                            'price': current_price,
                            'timestamp': datetime.now().isoformat(),
                            'approved': None,  # None means pending
                            'result': 'pending'
                        }

                        # Add to both the list (for frontend) and queue (for trading algorithm)
                        approvals, lock, queue_obj = get_user_pending_approvals(user_id)
                        with lock:
                            approvals.append(approval_request)

                        # Wait for user approval with timeout
                        approval_timeout = 30  # 30 seconds timeout
                        start_time = time.time()
                        approved = False

                        while time.time() - start_time < approval_timeout and not approved:
                            # Check if this trade has been approved/rejected from the queue
                            try:
                                check_approval = queue_obj.get_nowait()
                                if check_approval['id'] == trade_id:
                                    if check_approval['result'] == 'approved':
                                        approved = True
                                        transaction_result = execute_sell_transaction(user_id, current_price, selected_token, part_size, network)
                                        transaction_successful = transaction_result["success"]
                                    elif check_approval['result'] == 'rejected':
                                        transaction_successful = False
                                        print(f"[USER MODE] User rejected sell intent for {part_size} of {get_token_symbol(selected_token)} at ${current_price}")
                            except queue.Empty:
                                pass

                            if not approved:
                                time.sleep(0.5)  # Check more frequently

                        if not approved:
                            # Timeout - reject the trade
                            transaction_successful = False
                            print(f"[USER MODE] Timeout waiting for approval for sell intent")
                    else:  # automatic mode
                        transaction_result = execute_sell_transaction(user_id, current_price, selected_token, actual_sell_amount, network)
                        transaction_successful = transaction_result["success"]
                else:
                    # For devnet/testnet, just simulate
                    simulate_sell(current_price, selected_token, actual_sell_amount)
                    transaction_successful = True  # Simulation is always "successful"

                if transaction_successful:
                    # Only update state if transaction was successful
                    trading_state['last_action'] = 'sell'

                    # Record the number of sell operations completed before modifying arrays
                    sell_operations_completed = parts - len(trading_state['sell_parts'])

                    # When selling: reduce sell-parts by 1 (use a sell opportunity), increase buy-parts by 1 (create a buy opportunity)
                    if len(trading_state['sell_parts']) > 0:
                        # Remove a part from sell array (use up a sell opportunity)
                        trading_state['sell_parts'].pop()  # Remove from sell array
                        # Add a part to buy array (create a new buy opportunity)
                        if len(trading_state['buy_parts']) < parts:
                            trading_state['buy_parts'].append(len(trading_state['buy_parts']))  # Add to buy array

                    # Update base price to execution price (only on successful transaction)
                    trading_state['base_price'] = current_price

                    # Calculate profit from this sell
                    # In a real system, we'd track the purchase price for each part, but in this simplified system:
                    # profit per token = sell price - base price at time of sell
                    profit_per_token = current_price - current_base_price
                    total_profit = profit_per_token * part_size

                    # Account for transaction fees (estimated at $0.02 per transaction as requested)
                    estimated_fee = 0.02  # This is the requested fee amount
                    total_profit -= estimated_fee  # Subtract fee from profit
                    trading_state['total_profit'] += total_profit

                    # Reduce position when selling
                    trading_state['position'] -= min(part_size, trading_state['position'])
                    if trading_state['position'] <= 0:
                        trading_state['position'] = 0
                        trading_state['avg_purchase_price'] = 0

                    print(f"[TRADING] SELL: Used sell opportunity. Remaining buy opportunities: {len(trading_state['buy_parts'])}, Remaining sell opportunities: {len(trading_state['sell_parts'])} at {current_price}. New base price: {trading_state['base_price']}, Total profit: {trading_state['total_profit']}")

                    # Record transaction
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    tx_record = {
                        'timestamp': timestamp,
                        'action': 'sell',
                        'token': selected_token,
                        'token_symbol': get_token_symbol(selected_token),
                        'price': current_price,
                        'amount': part_size,  # Use part_size (USD value) for consistency with BUY
                        'base_price_at_execution': current_base_price,
                        'pnl': total_profit,  # P&L for sell transactions (after fee deduction)
                        'total_parts': parts,
                        'part_number': sell_operations_completed + 1,  # Number of sell operations completed + 1 to start from 1 (captured before array modification)
                        'execution_price': current_price,
                        'status': 'completed',  # New field to track transaction status
                        'buy_parts_count': len(trading_state['buy_parts']),
                        'sell_parts_count': len(trading_state['sell_parts']),
                        'fee_deducted': 0.02,  # Fee deducted from profit
                        'dollar_value': part_size  # Dollar value of the transaction
                    }

                    trading_state['transaction_history'].append(tx_record)

                    # Save to database
                    try:
                        trade = Trade(
                            user_id=user_id,
                            timestamp=timestamp,
                            action='sell',
                            token_symbol=get_token_symbol(selected_token),
                            token_mint=selected_token,
                            price=current_price,
                            amount=part_size, # Use part_size (USD value) for consistency with BUY
                            pnl=total_profit,
                            network=network,
                            status='completed'
                        )
                        trade.save()
                        # Increment trade count to trigger frontend refresh
                        trading_state['trade_count'] = trading_state.get('trade_count', 0) + 1
                        print(f"[TRADING] Saved SELL trade to database: {trade.id}")
                    except Exception as e:
                        print(f"[TRADING] Error saving trade to database: {e}")

                    # Keep only last 20 transactions
                    if len(trading_state['transaction_history']) > 20:
                        trading_state['transaction_history'] = trading_state['transaction_history'][-20:]
                else:
                    # Transaction failed, don't update base price or other state
                    print(f"[TRADING] SELL failed: Could not use sell opportunity. Remaining buy opportunities: {len(trading_state['buy_parts'])}, Remaining sell opportunities: {len(trading_state['sell_parts'])} at {current_price}. Base price unchanged: {trading_state['base_price']}")
                    # Don't move parts or update base price on failure

        except Exception as e:
            print(f"Error in trading algorithm: {e}")

        # Wait before next iteration (simulate real-time updates)
        time.sleep(5)

def get_jupiter_price_direct(input_mint, output_mint, amount):
    """Direct call to Jupiter API without using Flask request context"""
    import requests
    import urllib3

    # Disable SSL warnings if needed (for debugging purposes only)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Get Jupiter API key from environment
    jupiter_api_key = os.getenv('JUPITER_API_KEY')

    # Set appropriate headers for Jupiter API
    headers = {
        "x-api-key": jupiter_api_key
    }

    # First try the original pair with correct parameters
    params = {
        'inputMint': input_mint,
        'outputMint': output_mint,
        'amount': str(amount),  # Convert to string as required
        'swapMode': 'ExactIn',
        'slippageBps': 50,
        'restrictIntermediateTokens': 'true',
        'maxAccounts': 64,
        'instructionVersion': 'V1'
    }

    try:
        # Make the request with correct parameters
        response = requests.get(
            JUPITER_QUOTE_API,
            params=params,
            timeout=15,
            headers=headers,
            verify=True,  # Keep SSL verification enabled for security
            allow_redirects=True
        )

        if response.status_code == 200:
            quote_data = response.json()
            # Check if quote contains necessary data
            if 'outAmount' in quote_data and 'inAmount' in quote_data:
                out_amount = int(quote_data['outAmount'])
                in_amount = int(quote_data['inAmount'])

                # Price calculation with proper decimal adjustment
                if in_amount == 0:
                    return {"price": 0.0, "success": False, "message": "Input amount is zero"}

                # SOL (9 decimals) → USDC (6 decimals) price calculation
                price = (out_amount / 10**6) / (in_amount / 10**9)

                return {"price": price, "success": True, "quote_data": quote_data}
            else:
                return {"price": 0.0, "success": False, "message": f"Quote data missing: {quote_data}"}
        else:
            # If the API returns an error status, try to provide more useful error info
            error_text = response.text if response.text else f"HTTP {response.status_code}"
            return {"price": 0.0, "success": False, "message": f"API Error: {response.status_code} - {error_text}"}
    except requests.exceptions.ConnectionError as e:
        print(f"ConnectionError: {e}")
        return {"price": 0.0, "success": False, "message": f"Connection error - unable to reach Jupiter API: {str(e)}"}
    except requests.exceptions.Timeout as e:
        print(f"Timeout: {e}")
        return {"price": 0.0, "success": False, "message": f"Request timed out - Jupiter API is not responding: {str(e)}"}
    except requests.exceptions.RequestException as e:
        print(f"RequestException: {e}")
        return {"price": 0.0, "success": False, "message": f"Request error: {str(e)}"}
    except Exception as e:
        print(f"Unexpected error fetching price: {e}")
        # On error, return a default price and indicate failure
        return {"price": 0.0, "success": False, "message": str(e)}

def get_token_symbol(token_mint):
    """Get a display name for a token mint"""
    return TOKEN_INFO.get(token_mint, {}).get("symbol", f"Token_{token_mint[:8]}")

def execute_swap(user_id, input_mint, output_mint, amount, slippage_bps=50):
    """Execute a swap transaction using Jupiter API and private key"""
    try:
        # Get user's wallet from database
        wallet = Wallet.find_by_user_id(user_id)
        if not wallet:
            return {
                "success": False,
                "error": "Wallet not found for user"
            }

        # Get keypair
        keypair = wallet.get_keypair()
        if isinstance(keypair, bytes):
            # If we got raw bytes, we need to create the keypair properly
            try:
                from solana.keypair import Keypair as SolanaKeypair
                if len(keypair) == 64:
                    keypair = SolanaKeypair.from_secret_key(keypair)
                elif len(keypair) == 32:
                    keypair = SolanaKeypair.from_seed(keypair)
            except (ImportError, AttributeError):
                try:
                    from solders.keypair import Keypair as SolderKeypair
                    if len(keypair) == 64:
                        keypair = SolderKeypair.from_bytes(keypair)
                    elif len(keypair) == 32:
                        keypair = SolderKeypair.from_seed(keypair)
                except (ImportError, AttributeError):
                    raise ValueError("Could not create keypair from private key bytes")

        user_public_key = str(keypair.pubkey())

        # Get Jupiter API key
        jupiter_api_key = os.getenv('JUPITER_API_KEY')
        if not jupiter_api_key:
            raise ValueError("JUPITER_API_KEY not found in environment variables")

        # Get quote first
        quote_headers = {
            "x-api-key": jupiter_api_key
        }

        quote_params = {
            'inputMint': input_mint,
            'outputMint': output_mint,
            'amount': str(amount),  # Convert to string as required
            'swapMode': 'ExactIn',
            'slippageBps': slippage_bps,
            'restrictIntermediateTokens': 'true',
            'maxAccounts': 64,
            'instructionVersion': 'V1'
        }

        quote_response = requests.get(JUPITER_QUOTE_API, params=quote_params, headers=quote_headers)
        if quote_response.status_code != 200:
            raise Exception(f"Quote API error: {quote_response.status_code} - {quote_response.text}")

        quote_data = quote_response.json()

        # Prepare swap request
        swap_headers = {
            "Content-Type": "application/json",
            "x-api-key": jupiter_api_key
        }

        swap_body = {
            "userPublicKey": user_public_key,
            "quoteResponse": quote_data,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": {
                "priorityLevelWithMaxLamports": {
                    "priorityLevel": "medium",
                    "maxLamports": 100000,
                    "global": False
                }
            }
        }

        # Get swap transaction
        swap_response = requests.post(JUPITER_SWAP_API, headers=swap_headers, json=swap_body)
        if swap_response.status_code != 200:
            raise Exception(f"Swap API error: {swap_response.status_code} - {swap_response.text}")

        swap_data = swap_response.json()

        # Deserialize the transaction
        from base64 import b64decode
        from solders.transaction import VersionedTransaction
        from solders.rpc.config import RpcSendTransactionConfig
        from solders.commitment_config import CommitmentLevel

        transaction_data = b64decode(swap_data['swapTransaction'])

        # Create transaction object and sign it (for VersionedTransaction)
        tx = VersionedTransaction.from_bytes(transaction_data)

        # Sign the message
        from solders.message import to_bytes_versioned
        msg_bytes = to_bytes_versioned(tx.message)
        sig = keypair.sign_message(msg_bytes)

        # Populate signed transaction
        signed_tx = VersionedTransaction.populate(
            tx.message,
            [sig]
        )

        # Get the signed transaction bytes
        signed_transaction = bytes(signed_tx)

        # Get Helius API key for RPC
        helius_api_key = os.getenv('HELIUS_API_KEY')
        if helius_api_key:
            # Use Helius RPC endpoint for faster and more reliable transactions
            helius_rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_api_key}"
            solana_client = Client(helius_rpc_url)
        else:
            # Fallback to standard Solana RPC
            solana_client = Client("https://api.mainnet-beta.solana.com")

        from solana.rpc.types import TxOpts
        result = solana_client.send_raw_transaction(
            signed_transaction,
            opts=TxOpts(
                skip_preflight=False,
                preflight_commitment="confirmed"
            )
        )

        # Wait for confirmation
        signature = result.value
        confirmation = solana_client.confirm_transaction(signature, "confirmed")

        # Handle both object and list responses
        confirmation_value = confirmation.value
        if isinstance(confirmation_value, list):
            confirmation_value = confirmation_value[0] if confirmation_value else None

        if confirmation_value and hasattr(confirmation_value, 'err') and confirmation_value.err:
            raise Exception(f"Transaction failed: {confirmation_value.err}")
        elif confirmation_value and isinstance(confirmation_value, dict) and confirmation_value.get('err'):
            raise Exception(f"Transaction failed: {confirmation_value.get('err')}")

        # Transaction executed successfully
        return {
            "success": True,
            "signature": str(signature),
            "quote_data": quote_data,
            "swap_data": swap_data
        }

    except Exception as e:
        print(f"Error executing swap: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def execute_buy_transaction(user_id, price, token, amount, network="mainnet"):
    """Execute a real buy transaction using private key"""
    if network.lower() != "mainnet":
        # For devnet/testnet, just simulate
        token_symbol = get_token_symbol(token)
        print(f"[SIMULATION] Buying {amount} of {token_symbol} (mint: {token[:8]}...) at ${price:.8f} per unit")
        return {"success": True, "signature": "simulated", "message": "Simulated transaction"}

    # Check wallet balance before executing trade
    wallet = Wallet.find_by_user_id(user_id)
    if not wallet:
        return {"success": False, "error": "Wallet not found for user"}

    wallet_address = wallet.public_key

    # Get token balances
    balance_response = get_wallet_balance(wallet_address, network)
    if not balance_response.get("success", False):
        print(f"[FAILED] Could not check wallet balance: {balance_response.get('message', 'Unknown error')}")
        return {"success": False, "error": "Could not check wallet balance"}

    balances = balance_response.get("balances", [])

    # Determine input and output mints for the swap
    # If buying token, we're swapping from SOL/USDC to the token
    # For this example, assume we're swapping from USDC to the target token
    # If the token is SOL, we're swapping from USDC to SOL
    if token == "So11111111111111111111111111111111111111112":  # SOL
        input_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
        output_mint = token
        input_token_symbol = "USDC"
    else:
        input_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
        output_mint = token
        input_token_symbol = "USDC"

    # Find the input token balance
    input_balance = 0
    for balance_item in balances:
        if balance_item.get("token") == input_token_symbol:
            input_balance = balance_item.get("balance", 0)
            break

    # Calculate required amount including a reserved balance for fees
    # No reserved balance needed for USDC since fees are in SOL
    reserved_balance = 0.0  # No reserved balance for USDC
    required_amount = amount + reserved_balance

    # Check if there's enough SOL for transaction fees (always required)
    sol_balance = 0
    for balance_item in balances:
        if balance_item.get("token") == "SOL":
            sol_balance = balance_item.get("balance", 0)
            break

    # Ensure there's enough SOL to cover transaction fees
    if sol_balance < 0.005:
        print(f"[FAILED] Insufficient SOL for transaction fees: Have {sol_balance} SOL, need 0.005 SOL")
        return {"success": False, "error": f"Insufficient SOL for fees: Have {sol_balance}, need 0.005"}

    if input_balance < required_amount:
        print(f"[FAILED] Insufficient balance for buy: Have {input_balance} {input_token_symbol}, need {required_amount} {input_token_symbol}")
        return {"success": False, "error": f"Insufficient balance: Have {input_balance}, need {required_amount}"}

    # Convert amount to appropriate units based on the input token (USDC)
    # When buying, we're specifying how much of the output token we want to buy
    # So we need to determine how much input token to spend based on price
    # For now, we'll use the amount as is but convert to proper decimal units for USDC
    # This is a simplified conversion - in reality, we'd calculate based on desired output
    amount_units = int(amount * 10**6)  # Convert to USDC units (6 decimals)

    # Execute the swap
    result = execute_swap(user_id, input_mint, output_mint, amount_units)

    if result["success"]:
        token_symbol = get_token_symbol(token)
        print(f"[SUCCESS] Bought {amount} of {token_symbol} at ${price:.8f} per unit")
        print(f"Transaction signature: {result['signature']}")
        return result
    else:
        token_symbol = get_token_symbol(token)
        print(f"[FAILED] Failed to buy {amount} of {token_symbol} at ${price:.8f} per unit")
        print(f"Error: {result['error']}")
        return result

def execute_sell_transaction(user_id, price, token, amount, network="mainnet"):
    """Execute a real sell transaction using private key"""
    if network.lower() != "mainnet":
        # For devnet/testnet, just simulate
        token_symbol = get_token_symbol(token)
        print(f"[SIMULATION] Selling {amount} of {token_symbol} (mint: {token[:8]}...) at ${price:.8f} per unit")
        return {"success": True, "signature": "simulated", "message": "Simulated transaction"}

    # Check wallet balance before executing trade
    wallet = Wallet.find_by_user_id(user_id)
    if not wallet:
        return {"success": False, "error": "Wallet not found for user"}

    wallet_address = wallet.public_key

    # Get token balances
    balance_response = get_wallet_balance(wallet_address, network)
    if not balance_response.get("success", False):
        print(f"[FAILED] Could not check wallet balance: {balance_response.get('message', 'Unknown error')}")
        return {"success": False, "error": "Could not check wallet balance"}

    balances = balance_response.get("balances", [])

    # Determine input and output mints for the swap
    # If selling token, we're swapping from the token to SOL/USDC
    # For this example, assume we're swapping from the token to USDC
    # If the token is SOL, we're swapping from SOL to USDC
    if token == "So11111111111111111111111111111111111111112":  # SOL
        input_mint = token
        output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
        input_token_symbol = "SOL"
    else:
        input_mint = token
        output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
        input_token_symbol = get_token_symbol(token)

    # Find the input token balance
    input_balance = 0
    for balance_item in balances:
        if balance_item.get("token") == input_token_symbol:
            input_balance = balance_item.get("balance", 0)
            break

    # Calculate required amount including a reserved balance for fees
    # No reserved balance needed for the token being sold since fees are in SOL
    reserved_balance = 0.0  # No reserved balance for the token being sold
    required_amount = amount + reserved_balance

    # Check if there's enough SOL for transaction fees (always required)
    sol_balance = 0
    for balance_item in balances:
        if balance_item.get("token") == "SOL":
            sol_balance = balance_item.get("balance", 0)
            break

    # Ensure there's enough SOL to cover transaction fees
    if sol_balance < 0.005:
        print(f"[FAILED] Insufficient SOL for transaction fees: Have {sol_balance} SOL, need 0.005 SOL")
        return {"success": False, "error": f"Insufficient SOL for fees: Have {sol_balance}, need 0.005"}

    if input_balance < required_amount:
        print(f"[FAILED] Insufficient balance for sell: Have {input_balance} {input_token_symbol}, need {required_amount} {input_token_symbol}")
        return {"success": False, "error": f"Insufficient balance: Have {input_balance}, need {required_amount}"}

    # Convert amount to appropriate units based on the token being sold (input token)
    # For SOL, convert to SOL units (9 decimals)
    # For other tokens, assume 6 decimals like USDC
    if input_mint == "So11111111111111111111111111111111111111112":  # SOL
        # Convert to SOL units (9 decimals)
        amount_units = int(amount * 10**9)
    else:
        # Convert to token units (assuming 6 decimals like USDC for this example)
        amount_units = int(amount * 10**6)

    # Execute the swap
    result = execute_swap(user_id, input_mint, output_mint, amount_units)

    if result["success"]:
        token_symbol = get_token_symbol(token)
        print(f"[SUCCESS] Sold {amount} of {token_symbol} at ${price:.8f} per unit")
        print(f"Transaction signature: {result['signature']}")
        return result
    else:
        token_symbol = get_token_symbol(token)
        print(f"[FAILED] Failed to sell {amount} of {token_symbol} at ${price:.8f} per unit")
        print(f"Error: {result['error']}")
        return result

def simulate_buy(price, token, amount):
    """Simulate a buy transaction"""
    token_symbol = get_token_symbol(token)
    print(f"[SIMULATION] Buying {amount} of {token_symbol} (mint: {token[:8]}...) at ${price:.8f} per unit")
    # In a real simulation, we would update wallet balances, track positions, etc.
    # For now, we just log the action as we're not connecting to a real wallet

def simulate_sell(price, token, amount):
    """Simulate a sell transaction"""
    token_symbol = get_token_symbol(token)
    print(f"[SIMULATION] Selling {amount} of {token_symbol} (mint: {token[:8]}...) at ${price:.8f} per unit")
    # In a real simulation, we would update wallet balances, track positions, etc.
    # For now, we just log the action as we're not connecting to a real wallet")

@app.route('/api/add-funds', methods=['POST'])
@require_login
def add_funds():
    """This endpoint is now deprecated. Funds are added when user sends to their deposit address."""
    return jsonify({
        "success": False,
        "message": "This endpoint is deprecated. Use the deposit address to add funds."
    }), 400

@app.route('/api/deposit-address', methods=['GET'])
@require_login
def get_deposit_address():
    """Get the user's deposit address"""
    try:
        user_id = session['user_id']
        wallet = Wallet.find_by_user_id(user_id)

        if not wallet:
            return jsonify({"success": False, "message": "Wallet not found"}), 404

        return jsonify({
            "success": True,
            "deposit_address": wallet.public_key
        })
    except Exception as e:
        print(f"Error getting deposit address: {e}")
        return jsonify({"success": False, "message": f"Error getting deposit address: {str(e)}"}), 500

@app.route('/api/create-deposit-transaction', methods=['POST'])
@require_login
def create_deposit_transaction():
    """Create a deposit transaction for the user to sign"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        amount = float(data.get('amount', 0))

        if amount <= 0:
            return jsonify({"success": False, "message": "Amount must be greater than 0"}), 400

        # Get user's wallet (where funds will be deposited to)
        user_wallet = Wallet.find_by_user_id(user_id)
        if not user_wallet:
            return jsonify({"success": False, "message": "User wallet not found"}), 404

        # In a real implementation, we would create a transaction that transfers from the user's wallet to their trading bot wallet
        # For this, we need to use the Solana web3 library to create a transaction
        try:
            from solana.transaction import Transaction
            from solana.system_program import transfer, TransferParams
            from solana.publickey import PublicKey
            from spl.token.constants import TOKEN_PROGRAM_ID
            import base64

            # Get the user's deposit address (their trading bot wallet)
            destination_pubkey = PublicKey(user_wallet.public_key)

            # The transaction will be signed by the user's connected wallet (which we don't have access to here)
            # So we'll return the transaction details for the frontend to construct
            transaction_details = {
                "destination": str(destination_pubkey),
                "amount": amount,
                "token": "SOL"  # Default to SOL, could be extended for other tokens
            }

            return jsonify({
                "success": True,
                "transaction": transaction_details
            })

        except ImportError:
            # If solana libraries aren't available, return basic transaction info
            return jsonify({
                "success": True,
                "transaction": {
                    "destination": user_wallet.public_key,
                    "amount": amount,
                    "token": "SOL"
                },
                "message": "Transaction details prepared. Please send funds to the destination address."
            })

    except Exception as e:
        print(f"Error creating deposit transaction: {e}")
        return jsonify({"success": False, "message": f"Error creating deposit transaction: {str(e)}"}), 500

@app.route('/api/withdraw-funds', methods=['POST'])
@require_login
def withdraw_funds():
    """Withdraw funds from user's wallet to external address"""
    user_id = session['user_id']
    data = request.get_json()
    destination_address = data.get('destination_address')
    amount = float(data.get('amount', 0))
    token_mint = data.get('token_mint') # Mint address of the token to withdraw
    decimals = int(data.get('decimals', 9)) # Decimals for the token (default 9 for SOL)

    if not destination_address:
        return jsonify({"success": False, "message": "Destination address is required"}), 400

    if amount <= 0:
        return jsonify({"success": False, "message": "Amount must be greater than 0"}), 400
        
    if not token_mint:
         return jsonify({"success": False, "message": "Token mint is required"}), 400

    print(f"DEBUG: Withdrawal Request - Dest: {destination_address}, Amount: {amount}, Mint: {token_mint}, Decimals: {decimals}")

    try:
        # Get user's wallet
        wallet = Wallet.find_by_user_id(user_id)
        if not wallet:
            return jsonify({"success": False, "message": "Wallet not found"}), 404

        # Execute the transfer based on token type
        if token_mint == "So11111111111111111111111111111111111111112": # SOL
            result = execute_sol_transfer(user_id, destination_address, amount)
        else: # SPL Token
            result = execute_spl_transfer(user_id, destination_address, amount, token_mint, decimals)
            
        return jsonify(result)
    except Exception as e:
        print(f"Error withdrawing funds: {e}")
        return jsonify({"success": False, "message": f"Error withdrawing funds: {str(e)}"}), 500

def execute_sol_transfer(user_id, destination_address, amount):
    """Execute a real SOL transfer"""
    try:
        wallet = Wallet.find_by_user_id(user_id)
        keypair_data = wallet.get_keypair()
        
        # Handle keypair if it's bytes
        try:
            from solders.keypair import Keypair
            if isinstance(keypair_data, bytes):
                if len(keypair_data) == 64:
                    keypair = Keypair.from_bytes(keypair_data)
                elif len(keypair_data) == 32:
                    keypair = Keypair.from_seed(keypair_data)
                else:
                    return {"success": False, "message": f"Invalid keypair length: {len(keypair_data)}"}
            else:
                keypair = keypair_data
        except ImportError:
             return {"success": False, "message": "Could not import solders.keypair. Please ensure solders is installed."}
        
        # Determine RPC URL
        helius_api_key = os.getenv('HELIUS_API_KEY')
        if helius_api_key:
            rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_api_key}"
        else:
            rpc_url = "https://api.mainnet-beta.solana.com"
            
        client = Client(rpc_url)
        
        # Convert amount to lamports
        lamports = int(amount * 10**9)
        
        # Create transfer instruction
        try:
            from solders.system_program import transfer, TransferParams
            from solana.transaction import Transaction
            from solders.pubkey import Pubkey
            
            # Destination pubkey
            try:
                # Try creating Pubkey from string using solders
                if isinstance(destination_address, str):
                    dest_pubkey = Pubkey.from_string(destination_address)
                else:
                    dest_pubkey = destination_address
            except Exception as e:
                return {"success": False, "message": f"Invalid destination address: {str(e)}"}

            # Create transaction
            # Get latest blockhash (required for recent versions)
            recent_blockhash_resp = client.get_latest_blockhash()
            recent_blockhash = recent_blockhash_resp.value.blockhash
            
            tx = Transaction(recent_blockhash=recent_blockhash, fee_payer=keypair.pubkey())
            tx.add(transfer(TransferParams(
                from_pubkey=keypair.pubkey(),
                to_pubkey=dest_pubkey,
                lamports=lamports
            )))
            
            # Sign and send
            result = client.send_transaction(tx, keypair)
            
            signature = str(result.value)
            print(f"SOL Withdraw Success: https://solscan.io/tx/{signature}")
            
            return {
                "success": True, 
                "message": f"Successfully sent {amount} SOL. Signature: {signature}",
                "signature": signature
            }
            
        except Exception as inner_e:
            print(f"Error building/sending SOL tx: {inner_e}")
            raise inner_e

    except Exception as e:
        return {"success": False, "message": str(e)}

def execute_spl_transfer(user_id, destination_address, amount, token_mint, decimals):
    """Execute a real SPL token transfer"""
    try:
        wallet = Wallet.find_by_user_id(user_id)
        keypair_data = wallet.get_keypair()
        
        # Handle keypair if it's bytes
        try:
            from solders.keypair import Keypair
            if isinstance(keypair_data, bytes):
                if len(keypair_data) == 64:
                    keypair = Keypair.from_bytes(keypair_data)
                elif len(keypair_data) == 32:
                    keypair = Keypair.from_seed(keypair_data)
                else:
                    return {"success": False, "message": f"Invalid keypair length: {len(keypair_data)}"}
            else:
                keypair = keypair_data
        except ImportError:
             return {"success": False, "message": "Could not import solders.keypair. Please ensure solders is installed."}
        
        # Determine RPC URL
        helius_api_key = os.getenv('HELIUS_API_KEY')
        if helius_api_key:
            rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_api_key}"
        else:
            rpc_url = "https://api.mainnet-beta.solana.com"
            
        client = Client(rpc_url)
        
        # Convert amount to token units
        # Handle float precision issues
        amount_units = int(round(amount * (10**decimals)))
        
        print(f"DEBUG: SPL Transfer - Amount: {amount}, Decimals: {decimals}, Units: {amount_units}")
        
        # Imports for SPL token transfer
        from spl.token.instructions import get_associated_token_address, transfer_checked, TransferCheckedParams, create_associated_token_account
        from solana.transaction import Transaction
        from solders.pubkey import Pubkey
        from spl.token.constants import TOKEN_PROGRAM_ID
        
        # Handle Pubkey types compatibility
        try:
            if isinstance(token_mint, str):
                token_mint_pubkey = Pubkey.from_string(token_mint)
            else:
                token_mint_pubkey = token_mint
                
            if isinstance(destination_address, str):
                dest_pubkey_input = Pubkey.from_string(destination_address)
            else:
                dest_pubkey_input = destination_address
                
            source_owner_pubkey = keypair.pubkey()
        except Exception as e:
            return {"success": False, "message": f"Invalid address format: {str(e)}"}

        # Determine destination generic logic
        # Check if the inputs destination is a Wallet (System Account) or a Token Account
        dest_account_info_resp = client.get_account_info(dest_pubkey_input)
        
        is_dest_token_account = False
        if dest_account_info_resp.value:
            # Check owner
            owner_bytes = bytes(dest_account_info_resp.value.owner)
            token_program_bytes = bytes(TOKEN_PROGRAM_ID)
            if owner_bytes == token_program_bytes:
                is_dest_token_account = True
        
        # Get associated token accounts calculation
        source_ata = get_associated_token_address(source_owner_pubkey, token_mint_pubkey)
        
        if is_dest_token_account:
            # Destination IS the token account. Transfer directly to it.
            dest_ata = dest_pubkey_input
            print(f"DEBUG: Destination {destination_address} is a Token Account. Transferring directly.")
        else:
            # Destination is a Wallet Address. Derive the ATA.
            dest_ata = get_associated_token_address(dest_pubkey_input, token_mint_pubkey)
            print(f"DEBUG: Destination {destination_address} is a Wallet. Deriving ATA: {dest_ata}")

        # Get latest blockhash
        recent_blockhash_resp = client.get_latest_blockhash()
        recent_blockhash = recent_blockhash_resp.value.blockhash

        # Create transaction
        tx = Transaction(recent_blockhash=recent_blockhash, fee_payer=source_owner_pubkey)
        
        # Check if destination ATA exists (Only if we are using derived ATA)
        if not is_dest_token_account:
            dest_ata_info = client.get_account_info(dest_ata)
            if dest_ata_info.value is None:
                # Destination ATA does not exist, create it
                print(f"DEBUG: Creating missing ATA {dest_ata} for owner {dest_pubkey_input}")
                tx.add(create_associated_token_account(
                    payer=source_owner_pubkey,
                    owner=dest_pubkey_input,
                    mint=token_mint_pubkey
                ))

        tx.add(transfer_checked(TransferCheckedParams(
            program_id=TOKEN_PROGRAM_ID,
            source=source_ata,
            mint=token_mint_pubkey,
            dest=dest_ata,
            owner=source_owner_pubkey,
            amount=amount_units,
            decimals=decimals,
            signers=[source_owner_pubkey] # Added signers list
        )))
        
        # Sign and send
        result = client.send_transaction(tx, keypair)
        signature = str(result.value)
        print(f"SPL Withdraw Success: https://solscan.io/tx/{signature}")
        
        return {
            "success": True, 
            "message": f"Successfully sent {amount} tokens. Signature: {signature}",
            "signature": signature
        }

    except Exception as e:
        print(f"SPL Transfer Error: {e}")
        # Check for module not found error to give better feedback
        if "No module named" in str(e):
             return {"success": False, "message": f"Server Configuration Error: {str(e)}"}
        return {"success": False, "message": str(e)}

if __name__ == '__main__':
    app.run(debug=True, port=5000)