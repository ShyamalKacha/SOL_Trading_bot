from flask import Flask, render_template, request, jsonify
import requests
import json
try:
    from solana.publickey import PublicKey
    from solana.rpc.api import Client
except ImportError:
    # For compatibility if solana library structure changes
    try:
        from solders.pubkey import Pubkey as PublicKey
        from solana.rpc.api import Client
    except ImportError:
        # Mock objects for testing if libraries not available
        class PublicKey:
            def __init__(self, key):
                self.key = key
        class Client:
            pass

import threading
import time
from datetime import datetime

app = Flask(__name__)

# Constants
# Using the Jupiter Lite API endpoint for quotes (doesn't require API key)
JUPITER_QUOTE_API = "https://lite-api.jup.ag/swap/v1/quote"

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

# Token information mapping
TOKEN_INFO = {
    SOL_MINT: {"symbol": "SOL", "name": "Solana"},
    # SOL and wSOL have the same mint address but may be treated differently in UI
    # For display purposes, we'll treat them the same since they have the same underlying value
    "So11111111111111111111111111111111111111112": {"symbol": "SOL", "name": "Solana"},  # Standard SOL address
    USDC_MINT: {"symbol": "USDC", "name": "USD Coin"},
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

@app.route('/api/wallet-balance')
def get_wallet_balance_default():
    """Default route for wallet balance (for backward compatibility) - returns mock data"""
    return jsonify({
        "success": False,
        "message": "Wallet address required",
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

        # Determine the RPC URL based on the network
        if network.lower() == "devnet":
            rpc_url = "https://api.devnet.solana.com"
        elif network.lower() == "testnet":
            rpc_url = "https://api.testnet.solana.com"
        else:  # default to mainnet
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

    params = {
        'inputMint': input_mint,
        'outputMint': output_mint,
        'amount': amount,
        'slippageBps': 50  # 0.5% slippage
    }

    try:
        response = requests.get(JUPITER_QUOTE_API, params=params)
        if response.status_code == 200:
            quote_data = response.json()
            # Check if quote contains necessary data
            if 'outAmount' in quote_data and 'inAmount' in quote_data:
                out_amount = int(quote_data['outAmount'])
                in_amount = int(quote_data['inAmount'])
                # Price is output amount per input amount
                # Only return success if we have meaningful data
                if out_amount > 0 and in_amount > 0:
                    price = out_amount / in_amount
                    return jsonify({"price": price, "success": True})
                else:
                    return jsonify({"price": 0.0, "success": False, "message": "Invalid quote amounts returned"})
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

    # Validate required parameters
    required_fields = ['basePrice', 'upPercentage', 'downPercentage', 'selectedToken', 'tradeAmount', 'parts']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    base_price = float(data['basePrice'])
    up_percentage = float(data['upPercentage'])
    down_percentage = float(data['downPercentage'])
    selected_token = data['selectedToken']
    trade_amount = float(data['tradeAmount'])
    parts = int(data['parts'])

    # Validate that trade amount and parts are positive
    if trade_amount <= 0:
        return jsonify({"error": "Trade amount must be greater than 0"}), 400
    if parts <= 0:
        return jsonify({"error": "Parts must be greater than 0"}), 400

    # Stop any existing trading thread
    trading_state['is_running'] = False

    # Start new trading thread
    trading_thread = threading.Thread(
        target=trading_algorithm,
        args=(base_price, up_percentage, down_percentage, selected_token, trade_amount, parts)
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

def trading_algorithm(base_price, up_percentage, down_percentage, selected_token, trade_amount, parts):
    """Main trading algorithm with laddering effect - each transaction sets reference for next"""
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

    # Initialize the reference price for laddering effect
    # This price gets updated after each transaction and becomes the new reference for next threshold
    trading_state['reference_price'] = base_price  # Start with base price

    # Track the index of next part to trade (for sequential selling/buying)
    trading_state['next_sell_part_index'] = 0  # Next index to sell when price rises
    trading_state['next_buy_part_index'] = 0   # Next index to buy when price falls

    # Track individual parts: 0 = not traded, positive = bought at price, negative = sold at price
    trading_state['part_tracking'] = [0] * parts  # [0, 0, 0, 0] for 4 parts initially

    # Track which parts are currently available for trading
    # For selling: untraded parts are candidates for selling
    # For buying: sold parts are candidates for buying back
    trading_state['available_sell_parts'] = list(range(parts))  # [0, 1, 2, 3] - indices of parts to sell
    trading_state['available_buy_parts'] = []  # Indices of parts that were sold and can be bought back

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
            # Update the reference price to current market price when starting
            reference_price = initial_current_price
            trading_state['reference_price'] = reference_price  # Use reference price instead of dynamic_base_price for laddering
            trading_state['current_price'] = initial_current_price
            print(f"Updated reference price to initial current price: {reference_price}")
        else:
            # If initial price fetch fails, use the provided base price
            trading_state['reference_price'] = base_price
            trading_state['current_price'] = base_price
            print(f"Using provided base price: {base_price}")
    except Exception as e:
        print(f"Error getting initial price: {e}")
        trading_state['reference_price'] = base_price
        trading_state['current_price'] = base_price

    # Initialize parts tracking: 0 means not activated, negative means sold at that price, positive means bought at that price
    trading_state['part_tracking'] = [0] * parts  # [0, 0, 0, 0] for 4 parts initially

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
            # Update the base price to current market price when starting
            dynamic_base_price = initial_current_price
            trading_state['current_price'] = initial_current_price
            trading_state['dynamic_base_price'] = dynamic_base_price
            print(f"Updated base price to initial current price: {dynamic_base_price}")
        else:
            # If initial price fetch fails, use the provided base price
            trading_state['current_price'] = dynamic_base_price
            trading_state['dynamic_base_price'] = dynamic_base_price
            print(f"Using provided base price: {dynamic_base_price}")
    except Exception as e:
        print(f"Error getting initial price: {e}")
        trading_state['current_price'] = dynamic_base_price
        trading_state['dynamic_base_price'] = dynamic_base_price

    # Keep track of the price at which the last action was taken
    last_action_price = None

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
                # Update the dynamic base price in the trading state
                trading_state['dynamic_base_price'] = dynamic_base_price
                print(f"Got price: {current_price} for token {selected_token}, dynamic base: {dynamic_base_price}")
            else:
                print(f"Failed to get price for main pair: {price_response.get('message', 'Unknown error')}")

                # For tokens like Franklin that don't have price data in Jupiter,
                # we need to handle this case properly. We can either:
                # 1. Skip this iteration and wait for price availability
                # 2. Use a fallback mechanism
                # Since we can't trade what we can't price, we'll log the issue and continue
                print(f"No price available for token: {selected_token}, skipping this iteration")
                # Don't set a placeholder price - leave current_price as None or keep previous value
                # Use previous price if available, otherwise skip
                if trading_state['current_price'] is not None:
                    current_price = trading_state['current_price']  # Keep previous price
                    # Update the trading_state but skip the trading logic
                    trading_state['current_price'] = current_price
                else:
                    time.sleep(5)  # Wait before next iteration
                    continue  # Skip to the next iteration if no previous price

            # If we have a valid price (not 0 or None), proceed with trading logic
            if current_price is None or current_price <= 0:
                time.sleep(5)  # Wait before next iteration
                continue  # Skip trading logic if price is invalid

            # IMPLEMENT LADDERING LOGIC: Each transaction updates reference price for next transaction
            # Reference price gets updated after each buy/sell to the execution price
            action_taken = False
            part_tracking = trading_state['part_tracking']
            part_size = trading_state['part_size']
            reference_price = trading_state['reference_price']  # Use reference price for laddering effect

            # Calculate thresholds based on the current reference price
            sell_high_threshold = reference_price * (1 + up_percentage / 100)
            sell_low_threshold = reference_price * (1 - down_percentage / 100)

            # Determine if we should engage in trading based on current price vs reference thresholds
            should_trade = (current_price >= sell_high_threshold or current_price <= sell_low_threshold)

            if should_trade:
                part_to_process = None
                should_buy_part = False  # False = sell, True = buy

                # Use the reference price (instead of dynamic base) for laddering decisions
                if current_price >= sell_high_threshold:
                    # PRICE RISING - Look for sell opportunities with proper laddering logic
                    # 1. Look for parts currently held to sell (in reverse order - highest indices first) - parts were bought at lower prices
                    # 2. If no held parts to sell, sell the next unprocessed part

                    # Look for parts that were bought and are eligible for selling (at higher prices)
                    for i in range(len(part_tracking)-1, -1, -1):
                        if part_tracking[i] > 0:  # This part was bought at some price
                            buy_price = part_tracking[i]
                            sell_threshold = buy_price * (1 + up_percentage / 100)
                            if current_price >= sell_threshold:
                                part_to_process = i
                                should_buy_part = False  # SELL this part
                                break
                    if part_to_process is None:
                        # No parts to sell, so sell the next unprocessed part in sequence
                        for i in range(len(part_tracking)):
                            if part_tracking[i] == 0:  # This part hasn't been traded yet
                                part_to_process = i
                                should_buy_part = False  # SELL this unprocessed part
                                break
                elif current_price <= sell_low_threshold:
                    # PRICE FALLING - Look for buy opportunities with proper laddering logic
                    # 1. Look for parts that were previously sold to buy back (in reverse order - highest indices first)
                    # 2. If no parts to buy back, buy the next unprocessed part in sequence

                    # Look for parts that were sold and are eligible for buyback (at lower prices)
                    for i in range(len(part_tracking)-1, -1, -1):
                        if part_tracking[i] < 0:  # This part was sold at some price
                            sold_price = abs(part_tracking[i])
                            buyback_threshold = sold_price * (1 - down_percentage / 100)
                            if current_price <= buyback_threshold:
                                part_to_process = i
                                should_buy_part = True  # BUY back this part
                                break
                    if part_to_process is None:
                        # No parts to buy back, so buy the next unprocessed part in sequence
                        for i in range(len(part_tracking)):
                            if part_tracking[i] == 0:  # This part hasn't been traded yet
                                part_to_process = i
                                should_buy_part = True  # BUY this unprocessed part
                                break

                # Execute the operation if we found a part to process
                if part_to_process is not None:
                    # Record the action and update state
                    if should_buy_part:
                        # Buy this part
                        simulate_buy(current_price, selected_token, part_size)
                        trading_state['last_action'] = 'buy'
                        # Mark this part as bought (store the price as positive)
                        trading_state['part_tracking'][part_to_process] = current_price

                        # FOR LADDERING: Only update reference for NEW transactions (not for counter-trades)
                        # Check if this was a new buy (part was unprocessed) or a buyback (part was previously sold)
                        original_value = part_tracking[part_to_process]  # Get original value before update
                        if original_value == 0:  # This was a new buy (not a buyback)
                            trading_state['reference_price'] = current_price  # Update reference for future thresholds
                            print(f"[LADDERING-TRADING] NEW buy at {current_price}, updated reference: {trading_state['reference_price']}")
                        else:  # This is a buyback of previously sold part
                            print(f"[LADDERING-TRADING] Buyback at {current_price}, reference unchanged: {trading_state['reference_price']}")

                        # Update position and average purchase price
                        old_position_value = trading_state['position'] * trading_state['avg_purchase_price']
                        new_purchase_value = part_size * current_price
                        trading_state['position'] += part_size
                        if trading_state['position'] > 0:
                            trading_state['avg_purchase_price'] = (old_position_value + new_purchase_value) / trading_state['position']

                        action_taken = True
                        print(f"[LADDERING-TRADING] Part {part_to_process+1} BOUGHT at {current_price}. New reference price: {trading_state['reference_price']}")
                    else:
                        # Sell this part
                        simulate_sell(current_price, selected_token, part_size)
                        trading_state['last_action'] = 'sell'
                        # Mark this part as sold (store the price as negative)
                        trading_state['part_tracking'][part_to_process] = -current_price

                        # FOR LADDERING: Only update reference for NEW transactions (not for counter-trades)
                        # Check if this was a new sell (part was unprocessed) or a sellback (part was previously bought)
                        original_value = part_tracking[part_to_process]  # Get original value before update
                        if original_value == 0:  # This was a new sell (not a sellback)
                            trading_state['reference_price'] = current_price  # Update reference for future thresholds
                            print(f"[LADDERING-TRADING] NEW sell at {current_price}, updated reference: {trading_state['reference_price']}")
                        else:  # This is a sellback of previously bought part
                            print(f"[LADDERING-TRADING] Sellback at {current_price}, reference unchanged: {trading_state['reference_price']}")

                        # Update profit and position
                        # Calculate profit from this specific part based on when it was acquired
                        original_value = part_tracking[part_to_process]
                        if original_value < 0:  # This part was previously sold and is now being bought back
                            # Calculate profit based on the previous sell and current buyback price
                            previous_sell_price = abs(original_value)
                            profit_per_token = previous_sell_price - current_price  # Profit is previous sell price minus current buy price
                        elif original_value > 0:  # This part was bought previously and is now being sold
                            # Calculate profit based on the previous buy and current sell price
                            original_buy_price = original_value
                            profit_per_token = current_price - original_buy_price
                        else:  # This was an unprocessed part being sold initially
                            # Use the reference price as the cost basis for the initial sale
                            profit_per_token = current_price - trading_state['reference_price']  # Use the old reference price before updating it

                        total_profit_from_part = profit_per_token * part_size
                        trading_state['total_profit'] += total_profit_from_part

                        # Reduce position when selling
                        trading_state['position'] -= min(part_size, trading_state['position'])
                        if trading_state['position'] <= 0:
                            trading_state['position'] = 0
                            trading_state['avg_purchase_price'] = 0

                        action_taken = True
                        print(f"[LADDERING-TRADING] Part {part_to_process+1} SOLD at {current_price}. New reference price: {trading_state['reference_price']}, current_total_profit: {trading_state['total_profit']}")

            # Log action if taken
            if action_taken:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                action = trading_state['last_action']
                price = current_price

                # Calculate profit/loss for this transaction
                transaction_pnl = None
                current_part_size = trading_state['part_size']

                if action == 'sell':
                    # For sell, calculate profit from the price at which we bought this part
                    original_price = abs(part_tracking[part_to_process]) if part_tracking[part_to_process] < 0 else price
                    pnl_per_token = price - original_price
                    # Total P&L for the sold amount
                    transaction_pnl = pnl_per_token * current_part_size
                elif action == 'buy':
                    # For buy, P&L is not calculated until the part is sold again
                    transaction_pnl = None

                # Prepare transaction record
                tx_record = {
                    'timestamp': timestamp,
                    'action': action,
                    'token': selected_token,
                    'token_symbol': get_token_symbol(selected_token),  # Include the token symbol for display
                    'price': price,
                    'amount': current_part_size,  # Use part size for both buy and sell
                    'base_price_at_execution': trading_state['reference_price'],  # Use the laddering reference price at time of execution
                    'pnl': transaction_pnl,  # Record profit/loss for this transaction
                    'total_parts': len(part_tracking),  # Record total parts
                    'execution_price': price  # Record the price at which this part was traded
                }

                # Add part number for both buy and sell operations as both are part of the system
                tx_record['part_number'] = part_to_process + 1  # 1-indexed part number
                tx_record['original_price'] = abs(part_tracking[part_to_process]) if part_tracking[part_to_process] != 0 else price  # Store the original price for reference
                tx_record['part_status_before'] = part_tracking[part_to_process]  # Store the status before the transaction

                trading_state['transaction_history'].append(tx_record)

                # Keep only last 20 transactions
                if len(trading_state['transaction_history']) > 20:
                    trading_state['transaction_history'] = trading_state['transaction_history'][-20:]

        except Exception as e:
            print(f"Error in trading algorithm: {e}")

        # Wait before next iteration (simulate real-time updates)
        time.sleep(5)

def get_jupiter_price_direct(input_mint, output_mint, amount):
    """Direct call to Jupiter Lite API without using Flask request context"""
    import requests
    import urllib3

    # Disable SSL warnings if needed (for debugging purposes only)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Set appropriate headers for Jupiter Lite API
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }

    # First try the original pair
    params = {
        'inputMint': input_mint,
        'outputMint': output_mint,
        'amount': amount,
        'slippageBps': 50  # 0.5% slippage
    }

    try:
        # Make the request with more options to mimic a browser request
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
                # Calculate price accounting for decimals
                # For SOL/USDC pricing, we need to account for decimal differences
                # SOL has 9 decimals, USDC has 6 decimals (3 decimal difference)
                # If we're asking for SOL -> USDC, we might need to adjust for decimals

                # Price is output amount per input amount
                # Only return success if we have meaningful data
                if out_amount > 0 and in_amount > 0:
                    # Raw calculation before decimal adjustment
                    raw_price = out_amount / in_amount

                    # Apply proper decimal adjustment
                    # When dealing with SOL (9 decimals) and USDC (6 decimals),
                    # Jupiter returns raw amounts but for pricing we often need to adjust
                    # The difference in decimals is 9-6 = 3 decimals = factor of 1000

                    if (input_mint == "So11111111111111111111111111111111111111112" and  # SOL
                        output_mint == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"):   # USDC
                        # SOL -> USDC: Adjust for decimal difference (SOL: 9, USDC: 6, diff: 3)
                        # If Jupiter quotes 1 SOL (in lamports) -> X USDC (in raw units)
                        # The proper price in USD is X / 1000, but we need to consider what the raw ratio represents
                        # Actually, if Jupiter says for 1,000,000,000 lamports I get 133,000,000 USDC units
                        # That means 1 SOL gets me 133 USDC, so price should be 133
                        # The raw calculation gives 133,000,000 / 1,000,000,000 = 0.133
                        # So I need to multiply by 1000 to correct for the decimal difference
                        price = raw_price * (10 ** (9 - 6))  # 10^3 = 1000 factor
                    elif (input_mint == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" and  # USDC
                          output_mint == "So11111111111111111111111111111111111111112"):  # SOL
                        # USDC -> SOL: Adjust for decimal difference
                        # If Jupiter says 1 USDC gets X SOL, the price needs adjustment
                        price = raw_price / (10 ** (9 - 6))  # Invert the factor
                    else:
                        # For other tokens, use original calculation (may need adjustment later)
                        price = raw_price

                    # For debugging: print what tokens and the calculated price
                    print(f"Decimal-adjusted calculation: {input_mint} -> {output_mint}, "
                          f"raw_price: {raw_price}, adjusted_price: {price}")
                    return {"price": price, "success": True}
                else:
                    print(f"Invalid amounts received - out: {out_amount}, in: {in_amount}")
            else:
                print(f"Missing quote data in response: {quote_data}")

        # If first attempt failed, try reverse - if we want token price in USDC but token->USDC doesn't work,
        # try USDC->token and invert the price
        if input_mint != output_mint:  # Don't try if both mints are the same
            reverse_params = {
                'inputMint': output_mint,
                'outputMint': input_mint,
                'amount': amount,
                'slippageBps': 50
            }

            rev_response = requests.get(
                JUPITER_QUOTE_API,
                params=reverse_params,
                timeout=15,
                headers=headers,
                verify=True,
                allow_redirects=True
            )

            if rev_response.status_code == 200:
                rev_quote_data = rev_response.json()
                if 'outAmount' in rev_quote_data and 'inAmount' in rev_quote_data:
                    out_amount = int(rev_quote_data['outAmount'])
                    in_amount = int(rev_quote_data['inAmount'])
                    if out_amount > 0 and in_amount > 0:
                        # Invert the price for the reverse direction
                        price = in_amount / out_amount
                        return {"price": price, "success": True}

        # If both attempts failed, try with SOL as the intermediate currency
        # For example, if token->USDC doesn't work, try token->SOL->USDC
        if input_mint != "So11111111111111111111111111111111111111112" and output_mint != "So11111111111111111111111111111111111111112":
            # Try token -> SOL first
            sol_params = {
                'inputMint': input_mint,
                'outputMint': "So11111111111111111111111111111111111111112",  # SOL
                'amount': amount,
                'slippageBps': 50
            }

            sol_response = requests.get(
                JUPITER_QUOTE_API,
                params=sol_params,
                timeout=15,
                headers=headers,
                verify=True,
                allow_redirects=True
            )

            if sol_response.status_code == 200:
                sol_quote_data = sol_response.json()
                if 'outAmount' in sol_quote_data and 'inAmount' in sol_quote_data:
                    sol_out_amount = int(sol_quote_data['outAmount'])
                    sol_in_amount = int(sol_quote_data['inAmount'])
                    if sol_out_amount > 0 and sol_in_amount > 0:
                        # Now get SOL -> USDC
                        sol_to_usdc_params = {
                            'inputMint': "So11111111111111111111111111111111111111112",  # SOL
                            'outputMint': output_mint,  # USDC or other quote currency
                            'amount': sol_out_amount,  # amount of SOL we expect to get
                            'slippageBps': 50
                        }

                        sol_to_usdc_response = requests.get(
                            JUPITER_QUOTE_API,
                            params=sol_to_usdc_params,
                            timeout=15,
                            headers=headers,
                            verify=True,
                            allow_redirects=True
                        )

                        if sol_to_usdc_response.status_code == 200:
                            usdc_quote_data = sol_to_usdc_response.json()
                            if 'outAmount' in usdc_quote_data and 'inAmount' in usdc_quote_data:
                                usdc_out_amount = int(usdc_quote_data['outAmount'])
                                usdc_in_amount = int(usdc_quote_data['inAmount'])
                                if usdc_out_amount > 0 and usdc_in_amount > 0:
                                    # Calculate the final price through SOL intermediate
                                    # From token -> SOL: sol_out_amount / sol_in_amount
                                    # From SOL -> USDC: usdc_out_amount / usdc_in_amount
                                    # So token -> USDC = (sol_out_amount / sol_in_amount) * (usdc_out_amount / usdc_in_amount)
                                    price = (sol_out_amount / sol_in_amount) * (usdc_out_amount / usdc_in_amount)
                                    return {"price": price, "success": True}

        return {"price": 0.0, "success": False, "message": f"No price route found for {input_mint} -> {output_mint}"}
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