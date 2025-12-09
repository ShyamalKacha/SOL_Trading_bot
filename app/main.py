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
    required_fields = ['basePrice', 'upPercentage', 'downPercentage', 'selectedToken', 'tradeAmount']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    base_price = float(data['basePrice'])
    up_percentage = float(data['upPercentage'])
    down_percentage = float(data['downPercentage'])
    selected_token = data['selectedToken']
    trade_amount = float(data['tradeAmount'])

    # Validate that trade amount is positive
    if trade_amount <= 0:
        return jsonify({"error": "Trade amount must be greater than 0"}), 400

    # Stop any existing trading thread
    trading_state['is_running'] = False

    # Start new trading thread
    trading_thread = threading.Thread(
        target=trading_algorithm,
        args=(base_price, up_percentage, down_percentage, selected_token, trade_amount)
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

def trading_algorithm(base_price, up_percentage, down_percentage, selected_token, trade_amount):
    """Main trading algorithm with dynamic base price adjustment"""
    global trading_state
    trading_state['is_running'] = True
    trading_state['last_action'] = None

    # Start with the initial base price, but update to current price on start
    dynamic_base_price = base_price

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

            # Determine action based on current price and the dynamic base price
            sell_high_threshold = dynamic_base_price * (1 + up_percentage / 100)
            sell_low_threshold = dynamic_base_price * (1 - down_percentage / 100)

            action_taken = False

            # The logic should be:
            # 1. If current price is higher than sell_high_threshold and last action was buy, then sell
            # 2. If current price is lower than base_price and last action was sell (or no action), then buy
            # 3. Prevent consecutive same actions

            should_buy = current_price < dynamic_base_price and trading_state['last_action'] != 'buy'
            should_sell = (
                (current_price >= sell_high_threshold or current_price <= sell_low_threshold)
                and trading_state['last_action'] != 'sell'
            )

            if should_buy:
                simulate_buy(current_price, selected_token, trade_amount)
                trading_state['last_action'] = 'buy'
                # Update base price to the price at which we bought
                dynamic_base_price = current_price
                trading_state['dynamic_base_price'] = dynamic_base_price
                action_taken = True
                print(f"[TRADING ALGO] Buying at {current_price}, updated base: {dynamic_base_price}, sell_high: {sell_high_threshold}, sell_low: {sell_low_threshold}")
            elif should_sell:
                simulate_sell(current_price, selected_token, trade_amount)
                trading_state['last_action'] = 'sell'
                # Update base price to the price at which we sold
                dynamic_base_price = current_price
                trading_state['dynamic_base_price'] = dynamic_base_price
                action_taken = True
                print(f"[TRADING ALGO] Selling at {current_price}, updated base: {dynamic_base_price}, sell_high: {sell_high_threshold}, sell_low: {sell_low_threshold}")

            # Log action if taken
            if action_taken:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                action = trading_state['last_action']
                price = current_price
                trading_state['transaction_history'].append({
                    'timestamp': timestamp,
                    'action': action,
                    'token': selected_token,
                    'token_symbol': get_token_symbol(selected_token),  # Include the token symbol for display
                    'price': price,
                    'amount': trade_amount,
                    'base_price_at_execution': dynamic_base_price  # Record the dynamic base price at time of execution
                })

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