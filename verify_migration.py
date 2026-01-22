import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database import get_db, init_db
    from models.user import User
    from models.wallet import Wallet
    from models.trading_bot import TradingBot
    import pymongo
    print("Imports successful.")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def verify():
    print("Testing MongoDB connection...")
    try:
        db = get_db()
        print(f"Connected to database: {db.name}")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    print("Initializing indexes...")
    try:
        init_db()
    except Exception as e:
        print(f"Index initialization failed: {e}")
        return

    print("Testing User model...")
    try:
        # Create test user
        email = f"test_{os.urandom(4).hex()}@example.com"
        user = User(email=email)
        user.set_password("password123")
        user.save()
        print(f"User created with ID: {user.id}")
        
        # Find user
        found_user = User.find_by_email(email)
        if found_user and found_user.id == user.id:
            print("User found by email.")
        else:
            print("User NOT found by email.")
            
        found_user_id = User.find_by_id(user.id)
        if found_user_id and found_user_id.email == email:
            print("User found by ID.")
        else:
            print("User NOT found by ID.")

    except Exception as e:
        print(f"User model test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify()
