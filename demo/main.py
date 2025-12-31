from flask import Flask, render_template, request, jsonify
import requests
import json
from dotenv import load_dotenv
import os
# Updated trading algorithm implementation
# Try to import from solders first (modern library), then fall back to older solana library
try:
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey as PublicKey
    USING_SOLDERS = True
except ImportError:
    USING_SOLDERS = False
    try:
        from solana.keypair import Keypair
        from solana.publickey import PublicKey
    except ImportError:
        # Mock objects for testing if libraries not available
        class PublicKey:
            def __init__(self, key):
                self.key = key
        class Keypair:
            pass

# Import RPC client
try:
    from solana.rpc.api import Client
    from solana.transaction import Transaction
except ImportError:
    class Client:
        pass
    class Transaction:
        pass

# Load environment variables
load_dotenv()

import threading
import time
from datetime import datetime

app = Flask(__name__)

# Constants
# Using the Jupiter API endpoint for quotes (requires API key)
JUPITER_QUOTE_API = "https://api.jup.ag/swap/v1/quote"
JUPITER_SWAP_API = "https://api.jup.ag/swap/v1/swap"

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

# Global variables to store trading state
trading_state = {
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
}

@app.route('/')
def index():
    return render_template('index.html', tokens=MOCK_TOKENS)

@app.route('/api/wallet-info')
def get_wallet_info():
    """Get wallet address derived from the private key in .env"""
    try:
        wallet_address = get_wallet_address()
        if not wallet_address:
            return jsonify({
                "success": False,
                "message": "Could not retrieve wallet address from private key. Please check SOLANA_PRIVATE_KEY in .env file.",
                "wallet_address": None
            })
        
        return jsonify({
            "success": True,
            "wallet_address": wallet_address
        })
    except Exception as e:
        print(f"Error in get_wallet_info: {e}")
        return jsonify({
            "success": False,
            "message": f"Error getting wallet info: {str(e)}",
            "wallet_address": None
        })

@app.route('/api/wallet-balance')
def get_wallet_balance_default():
    """Default route for wallet balance - returns balance for the private key wallet"""
    try:
        wallet_address = get_wallet_address()
        if not wallet_address:
            return jsonify({
                "success": False,
                "message": "Could not retrieve wallet address from private key",
                "balances": []
            })

        return get_wallet_balance(wallet_address, "mainnet")
    except Exception as e:
        print(f"Error in get_wallet_balance_default: {e}")
        return jsonify({
            "success": False,
            "message": f"Error connecting to wallet: {str(e)}",
            "balances": []
        })

@app.route('/api/wallet-balance/<wallet_address>')
@app.route('/api/wallet-balance/<wallet_address>/<network>')
def get_wallet_balance(wallet_address, network="mainnet"):
    """Function to get real wallet token balances from Solana blockchain"""
    try:
        # Validate wallet address format (basic check)
        if len(wallet_address) < 32 or len(wallet_address) > 44:
            return jsonify({
                "success": False,
                "message": "Invalid wallet address format",
                "balances": []
            })

        # Determine the RPC URL based on the network and check for Helius API key
        helius_api_key = os.getenv('HELIUS_API_KEY')

        if network.lower() == "devnet":
            if helius_api_key:
                rpc_url = f"https://devnet.helius-rpc.com/?api-key={helius_api_key}"
            else:
                rpc_url = "https://api.devnet.solana.com"
        elif network.lower() == "testnet":
            if helius_api_key:
                rpc_url = f"https://testnet.helius-rpc.com/?api-key={helius_api_key}"
            else:
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

        return jsonify({
            "success": True,
            "balances": balances
        })

    except Exception as e:
        print(f"Error in get_wallet_balance: {e}")
        return jsonify({
            "success": False,
            "message": f"Error connecting to wallet: {str(e)}",
            "balances": []
        })

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
def start_trading():
    """Start the trading algorithm"""
    global trading_state
    data = request.get_json()

    # Validate required parameters (removed basePrice since it's now automatically set)
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

    # Stop any existing trading thread
    trading_state['is_running'] = False

    # Start new trading thread - the algorithm will fetch current price and use it as base
    trading_thread = threading.Thread(
        target=trading_algorithm,
        args=(0, up_percentage, down_percentage, selected_token, trade_amount, parts, network, trading_mode)  # Pass 0 as placeholder for base_price
    )
    trading_thread.daemon = True
    trading_thread.start()

    return jsonify({"message": "Trading started"})

@app.route('/api/stop-trading', methods=['POST'])
def stop_trading():
    """Stop the trading algorithm"""
    global trading_state
    trading_state['is_running'] = False
    return jsonify({"message": "Trading stopped"})

@app.route('/api/trading-status')
def get_trading_status():
    """Get current trading status"""
    # Ensure dynamic base price is present in response
    status = trading_state.copy()
    # If dynamic_base_price is not set, default to the original base price concept
    if 'dynamic_base_price' not in status or status['dynamic_base_price'] is None:
        status['dynamic_base_price'] = status.get('original_base_price', 0)
    return jsonify(status)

def trading_algorithm(base_price, up_percentage, down_percentage, selected_token, trade_amount, parts, network="mainnet", trading_mode="automatic"):
    """Main trading algorithm with correct laddering logic - each transaction updates the base price"""
    global trading_state
    trading_state['is_running'] = True
    trading_state['last_action'] = None
    trading_state['total_profit'] = 0  # Track total profit
    trading_state['position'] = 0  # Track number of tokens held
    trading_state['avg_purchase_price'] = 0  # Track average purchase price

    # Calculate amount per part
    part_size = trade_amount / parts
    trading_state['parts'] = parts
    trading_state['part_size'] = part_size

    # Track consecutive buy/sell operations
    trading_state['consecutive_buys'] = 0
    trading_state['consecutive_sells'] = 0

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

            # Determine if we should buy or sell based on current price vs thresholds
            should_buy = current_price <= buy_threshold and trading_state['consecutive_buys'] < parts
            should_sell = current_price >= sell_threshold and trading_state['consecutive_sells'] < parts

            # Execute buy/sell based on conditions - note that we can switch between buy and sell at any time
            if should_buy:
                # BUY operation
                transaction_successful = False

                # Execute real transaction if on mainnet, otherwise simulate
                if network.lower() == "mainnet":
                    # Check trading mode
                    if trading_mode == "user":
                        # In user mode, we need to wait for user confirmation
                        # For now, we'll implement a simplified version where we just log the intent
                        # In a real implementation, we'd need to implement a notification system
                        print(f"[USER MODE] Buy intent: {part_size} of {get_token_symbol(selected_token)} at ${current_price}")
                        # For this implementation, we'll assume user accepted (in real app, this would be interactive)
                        transaction_result = execute_buy_transaction(current_price, selected_token, part_size, network)
                        transaction_successful = transaction_result["success"]
                    else:  # automatic mode
                        transaction_result = execute_buy_transaction(current_price, selected_token, part_size, network)
                        transaction_successful = transaction_result["success"]
                else:
                    # For devnet/testnet, just simulate
                    simulate_buy(current_price, selected_token, part_size)
                    transaction_successful = True  # Simulation is always "successful"

                if transaction_successful:
                    # Only update state if transaction was successful
                    trading_state['last_action'] = 'buy'

                    # Update consecutive counters
                    trading_state['consecutive_buys'] += 1
                    trading_state['consecutive_sells'] = 0  # Reset consecutive sells counter

                    # Update base price to execution price (only on successful transaction)
                    trading_state['base_price'] = current_price

                    # Update position and average purchase price
                    old_position_value = trading_state['position'] * trading_state['avg_purchase_price']
                    new_purchase_value = part_size * current_price
                    trading_state['position'] += part_size
                    if trading_state['position'] > 0:
                        trading_state['avg_purchase_price'] = (old_position_value + new_purchase_value) / trading_state['position']

                    print(f"[TRADING] BUY: Part {trading_state['consecutive_buys']} of {parts} bought at {current_price}. New base price: {trading_state['base_price']}")

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
                        'part_number': trading_state['consecutive_buys'],
                        'execution_price': current_price,
                        'status': 'completed'  # New field to track transaction status
                    }

                    trading_state['transaction_history'].append(tx_record)

                    # Keep only last 20 transactions
                    if len(trading_state['transaction_history']) > 20:
                        trading_state['transaction_history'] = trading_state['transaction_history'][-20:]
                else:
                    # Transaction failed, don't update base price or other state
                    print(f"[TRADING] BUY failed: Part {trading_state['consecutive_buys'] + 1} of {parts} failed at {current_price}. Base price unchanged: {trading_state['base_price']}")
                    # Don't increment consecutive counters or update base price on failure

            elif should_sell:
                # SELL operation
                transaction_successful = False

                # Execute real transaction if on mainnet, otherwise simulate
                if network.lower() == "mainnet":
                    # Check trading mode
                    if trading_mode == "user":
                        # In user mode, we need to wait for user confirmation
                        print(f"[USER MODE] Sell intent: {part_size} of {get_token_symbol(selected_token)} at ${current_price}")
                        # For this implementation, we'll assume user accepted (in real app, this would be interactive)
                        transaction_result = execute_sell_transaction(current_price, selected_token, part_size, network)
                        transaction_successful = transaction_result["success"]
                    else:  # automatic mode
                        transaction_result = execute_sell_transaction(current_price, selected_token, part_size, network)
                        transaction_successful = transaction_result["success"]
                else:
                    # For devnet/testnet, just simulate
                    simulate_sell(current_price, selected_token, part_size)
                    transaction_successful = True  # Simulation is always "successful"

                if transaction_successful:
                    # Only update state if transaction was successful
                    trading_state['last_action'] = 'sell'

                    # Update consecutive counters
                    trading_state['consecutive_sells'] += 1
                    trading_state['consecutive_buys'] = 0  # Reset consecutive buys counter

                    # Update base price to execution price (only on successful transaction)
                    trading_state['base_price'] = current_price

                    # Calculate profit from this sell
                    # In a real system, we'd track the purchase price for each part, but in this simplified system:
                    # profit per token = sell price - base price at time of sell
                    profit_per_token = current_price - current_base_price
                    total_profit = profit_per_token * part_size
                    trading_state['total_profit'] += total_profit

                    # Reduce position when selling
                    trading_state['position'] -= min(part_size, trading_state['position'])
                    if trading_state['position'] <= 0:
                        trading_state['position'] = 0
                        trading_state['avg_purchase_price'] = 0

                    print(f"[TRADING] SELL: Part {trading_state['consecutive_sells']} of {parts} sold at {current_price}. New base price: {trading_state['base_price']}, Total profit: {trading_state['total_profit']}")

                    # Record transaction
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    tx_record = {
                        'timestamp': timestamp,
                        'action': 'sell',
                        'token': selected_token,
                        'token_symbol': get_token_symbol(selected_token),
                        'price': current_price,
                        'amount': part_size,
                        'base_price_at_execution': current_base_price,
                        'pnl': total_profit,  # P&L for sell transactions
                        'total_parts': parts,
                        'part_number': trading_state['consecutive_sells'],
                        'execution_price': current_price,
                        'status': 'completed'  # New field to track transaction status
                    }

                    trading_state['transaction_history'].append(tx_record)

                    # Keep only last 20 transactions
                    if len(trading_state['transaction_history']) > 20:
                        trading_state['transaction_history'] = trading_state['transaction_history'][-20:]
                else:
                    # Transaction failed, don't update base price or other state
                    print(f"[TRADING] SELL failed: Part {trading_state['consecutive_sells'] + 1} of {parts} failed at {current_price}. Base price unchanged: {trading_state['base_price']}")
                    # Don't increment consecutive counters or update base price on failure

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

def get_private_key():
    """Get the private key from environment variables.
    Supports multiple formats:
    - Hex string (64 or 128 characters, with or without 0x prefix)
    - Base58 encoded string (common export format from Phantom, Solflare)
    - JSON array of numbers (Solana CLI format)
    """
    private_key_str = os.getenv('SOLANA_PRIVATE_KEY')
    if not private_key_str:
        raise ValueError("SOLANA_PRIVATE_KEY not found in environment variables")
    
    private_key_str = private_key_str.strip()
    
    # Try JSON array format first (e.g., [1,2,3,...])
    if private_key_str.startswith('['):
        try:
            import json
            key_array = json.loads(private_key_str)
            return bytes(key_array)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Failed to parse JSON array format: {e}")
    
    # Try hex format (with or without 0x prefix)
    if private_key_str.startswith('0x'):
        private_key_str = private_key_str[2:]
    
    # Check if it looks like hex (only hex characters)
    if all(c in '0123456789abcdefABCDEF' for c in private_key_str):
        try:
            return bytes.fromhex(private_key_str)
        except ValueError as e:
            print(f"Failed to parse hex format: {e}")
    
    # Try base58 format (common export format from wallets like Phantom)
    try:
        import base58
        return base58.b58decode(private_key_str)
    except Exception as e:
        print(f"Failed to parse base58 format: {e}")
    
    raise ValueError("Could not parse SOLANA_PRIVATE_KEY. Supported formats: hex string, base58 string, or JSON array.")

def get_wallet_address():
    """Get the wallet address from the private key"""
    try:
        private_key_bytes = get_private_key()
        
        # solders uses from_bytes(), older solana library uses from_secret_key()
        if USING_SOLDERS:
            # solders expects 64 bytes (secret key + public key) or just 32 bytes (secret key)
            if len(private_key_bytes) == 64:
                keypair = Keypair.from_bytes(private_key_bytes)
            elif len(private_key_bytes) == 32:
                # Only seed provided, need to derive keypair
                keypair = Keypair.from_seed(private_key_bytes)
            else:
                raise ValueError(f"Invalid key length: {len(private_key_bytes)} bytes. Expected 32 or 64.")
            return str(keypair.pubkey())
        else:
            # Older solana library
            keypair = Keypair.from_secret_key(private_key_bytes)
            return str(keypair.public_key)
    except Exception as e:
        print(f"Error getting wallet address: {e}")
        return None

def execute_swap(input_mint, output_mint, amount, slippage_bps=50):
    """Execute a swap transaction using Jupiter API and private key"""
    try:
        # Get private key and create keypair
        private_key_bytes = get_private_key()
        
        # solders uses from_bytes(), older solana library uses from_secret_key()
        if USING_SOLDERS:
            if len(private_key_bytes) == 64:
                keypair = Keypair.from_bytes(private_key_bytes)
            elif len(private_key_bytes) == 32:
                keypair = Keypair.from_seed(private_key_bytes)
            else:
                raise ValueError(f"Invalid key length: {len(private_key_bytes)} bytes")
            user_public_key = str(keypair.pubkey())
        else:
            keypair = Keypair.from_secret_key(private_key_bytes)
            user_public_key = str(keypair.public_key)

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
        transaction_data = b64decode(swap_data['swapTransaction'])

        # Create transaction object and sign it
        transaction = Transaction.deserialize(transaction_data)
        transaction.sign([keypair])

        # Serialize the signed transaction
        signed_transaction = transaction.serialize()

        # Get Helius API key for RPC
        helius_api_key = os.getenv('HELIUS_API_KEY')
        if helius_api_key:
            # Use Helius RPC endpoint for faster and more reliable transactions
            helius_rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_api_key}"
            solana_client = Client(helius_rpc_url)
        else:
            # Fallback to standard Solana RPC
            solana_client = Client("https://api.mainnet-beta.solana.com")

        result = solana_client.send_raw_transaction(signed_transaction)

        # Wait for confirmation
        from solana.rpc.commitment import Confirmed
        signature = result.value
        confirmation = solana_client.confirm_transaction(signature, Confirmed)

        if confirmation.value.err:
            raise Exception(f"Transaction failed: {confirmation.value.err}")

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

def execute_buy_transaction(price, token, amount, network="mainnet"):
    """Execute a real buy transaction using private key"""
    if network.lower() != "mainnet":
        # For devnet/testnet, just simulate
        token_symbol = get_token_symbol(token)
        print(f"[SIMULATION] Buying {amount} of {token_symbol} (mint: {token[:8]}...) at ${price:.8f} per unit")
        return {"success": True, "signature": "simulated", "message": "Simulated transaction"}

    # Determine input and output mints for the swap
    # If buying token, we're swapping from SOL/USDC to the token
    # For this example, assume we're swapping from USDC to the target token
    # If the token is SOL, we're swapping from USDC to SOL
    if token == "So11111111111111111111111111111111111111112":  # SOL
        input_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
        output_mint = token
    else:
        input_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
        output_mint = token

    # Convert amount to appropriate units (assuming USDC has 6 decimals and SOL has 9)
    # This is a simplified conversion - in reality, we'd need to know the specific token decimals
    if input_mint == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v":  # USDC
        # Convert to USDC units (6 decimals)
        amount_units = int(amount * 10**6)
    else:
        # Convert to SOL units (9 decimals)
        amount_units = int(amount * 10**9)

    # Execute the swap
    result = execute_swap(input_mint, output_mint, amount_units)

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

def execute_sell_transaction(price, token, amount, network="mainnet"):
    """Execute a real sell transaction using private key"""
    if network.lower() != "mainnet":
        # For devnet/testnet, just simulate
        token_symbol = get_token_symbol(token)
        print(f"[SIMULATION] Selling {amount} of {token_symbol} (mint: {token[:8]}...) at ${price:.8f} per unit")
        return {"success": True, "signature": "simulated", "message": "Simulated transaction"}

    # Determine input and output mints for the swap
    # If selling token, we're swapping from the token to SOL/USDC
    # For this example, assume we're swapping from the token to USDC
    # If the token is SOL, we're swapping from SOL to USDC
    if token == "So11111111111111111111111111111111111111112":  # SOL
        input_mint = token
        output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
    else:
        input_mint = token
        output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC

    # Convert amount to appropriate units (assuming USDC has 6 decimals and SOL has 9)
    # This is a simplified conversion - in reality, we'd need to know the specific token decimals
    if input_mint == "So11111111111111111111111111111111111111112":  # SOL
        # Convert to SOL units (9 decimals)
        amount_units = int(amount * 10**9)
    else:
        # Convert to token units (assuming 6 decimals like USDC for this example)
        amount_units = int(amount * 10**6)

    # Execute the swap
    result = execute_swap(input_mint, output_mint, amount_units)

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
    # For now, we just log the action as we're not connecting to a real wallet

if __name__ == '__main__':
    app.run(debug=True, port=5000)