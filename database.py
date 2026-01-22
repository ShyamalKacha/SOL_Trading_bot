import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

_db = None

def get_db():
    global _db
    if _db is None:
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/trading_bot')
        client = MongoClient(mongo_uri)
        # Verify connection
        try:
            client.admin.command('ping')
            print("Connected to MongoDB successfully")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            raise e
            
        db_name = mongo_uri.split('/')[-1].split('?')[0]  # Extract db name from URI
        if not db_name:
             db_name = 'trading_bot' # Default if not specified in URI

        _db = client[db_name]
        
    return _db

def init_db():
    """Initialize database indexes"""
    db = get_db()
    
    # User indexes
    db.users.create_index("email", unique=True)
    
    # Wallet indexes
    db.wallets.create_index("public_key", unique=True)
    db.wallets.create_index("user_id") # Foreign key equivalent
    
    # TradingBot indexes
    db.trading_bots.create_index("user_id") # Foreign key equivalent

    print("Database indexes initialized")
