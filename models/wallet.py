"""
Wallet model for the multi-user Solana trading bot
"""
import sqlite3
from datetime import datetime
from cryptography.fernet import Fernet
import json
import os
try:
    from solana.keypair import Keypair
    from solana.publickey import PublicKey
except ImportError:
    # For compatibility if solana library structure changes
    try:
        from solders.keypair import Keypair
        from solders.pubkey import Pubkey as PublicKey
    except ImportError:
        # Mock objects for testing if libraries not available
        class Keypair:
            def __init__(self, *args, **kwargs):
                pass
            @classmethod
            def generate(cls):
                return cls()
            def to_bytes(self):
                return b'\x00' * 64
        class PublicKey:
            def __init__(self, *args, **kwargs):
                pass
            def __str__(self):
                return "mock_public_key"


class Wallet:
    def __init__(self, id=None, user_id=None, public_key=None, encrypted_private_key=None, created_at=None, balance=None):
        self.id = id
        self.user_id = user_id
        self.public_key = public_key
        self.encrypted_private_key = encrypted_private_key
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.balance = balance or {}

    @staticmethod
    def create_table():
        """Create the wallets table if it doesn't exist"""
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                public_key TEXT UNIQUE NOT NULL,
                encrypted_private_key TEXT NOT NULL,
                created_at TEXT NOT NULL,
                balance TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def save(self):
        """Save wallet to database"""
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        if self.id:
            cursor.execute('''
                UPDATE wallets 
                SET user_id=?, public_key=?, encrypted_private_key=?, balance=?
                WHERE id=?
            ''', (self.user_id, self.public_key, self.encrypted_private_key, json.dumps(self.balance), self.id))
        else:
            cursor.execute('''
                INSERT INTO wallets (user_id, public_key, encrypted_private_key, created_at, balance)
                VALUES (?, ?, ?, ?, ?)
            ''', (self.user_id, self.public_key, self.encrypted_private_key, self.created_at, json.dumps(self.balance)))
            self.id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return self

    @staticmethod
    def find_by_user_id(user_id):
        """Find wallet by user ID"""
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM wallets WHERE user_id=?', (user_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return Wallet(
                id=row[0],
                user_id=row[1],
                public_key=row[2],
                encrypted_private_key=row[3],
                created_at=row[4],
                balance=json.loads(row[5])
            )
        return None

    @staticmethod
    def find_by_public_key(public_key):
        """Find wallet by public key"""
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM wallets WHERE public_key=?', (public_key,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return Wallet(
                id=row[0],
                user_id=row[1],
                public_key=row[2],
                encrypted_private_key=row[3],
                created_at=row[4],
                balance=json.loads(row[5])
            )
        return None

    @staticmethod
    def create_wallet_for_user(user_id):
        """Create a new wallet for a user"""
        # Generate a new Solana keypair
        keypair = Keypair.generate()
        private_key_bytes = keypair.to_bytes()
        
        # Encrypt the private key
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            # Generate a new key if one doesn't exist
            encryption_key = Fernet.generate_key().decode()
            print(f"Generated encryption key: {encryption_key}")
            print("Please set this as ENCRYPTION_KEY in your .env file")
        
        fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        encrypted_private_key = fernet.encrypt(private_key_bytes).decode()
        
        # Create the wallet
        wallet = Wallet(
            user_id=user_id,
            public_key=str(keypair.pubkey()),
            encrypted_private_key=encrypted_private_key
        )
        
        return wallet.save()

    def get_private_key(self):
        """Decrypt and return the private key"""
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY not set in environment")
        
        fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        decrypted_private_key = fernet.decrypt(self.encrypted_private_key.encode())
        
        return decrypted_private_key

    def update_balance(self, new_balance):
        """Update wallet balance"""
        # Convert list format to dict format if needed
        if isinstance(new_balance, list):
            balance_dict = {}
            for item in new_balance:
                if isinstance(item, dict) and 'token' in item and 'balance' in item:
                    balance_dict[item['token']] = item['balance']
            self.balance = balance_dict
        else:
            self.balance = new_balance

        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE wallets
            SET balance=?
            WHERE id=?
        ''', (json.dumps(self.balance), self.id))

        conn.commit()
        conn.close()