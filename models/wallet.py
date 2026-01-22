"""
Wallet model for the multi-user Solana trading bot
"""
from datetime import datetime
from cryptography.fernet import Fernet
import json
import os
from database import get_db
from bson.objectid import ObjectId

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
    def __init__(self, id=None, user_id=None, public_key=None, encrypted_private_key=None, created_at=None, balance=None, _id=None):
        self._id = _id if _id else (ObjectId(id) if id else None)
        self.user_id = user_id
        self.public_key = public_key
        self.encrypted_private_key = encrypted_private_key
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.balance = balance or {}

    @property
    def id(self):
        return str(self._id) if self._id else None
        
    @id.setter
    def id(self, value):
        if value:
            self._id = ObjectId(value)
        else:
            self._id = None

    @staticmethod
    def create_table():
        """Create the wallets table if it doesn't exist"""
        pass

    def save(self):
        """Save wallet to database"""
        db = get_db()
        
        # Ensure user_id is ObjectId for reference
        user_id_obj = ObjectId(self.user_id) if isinstance(self.user_id, str) else self.user_id

        wallet_data = {
            "user_id": user_id_obj,
            "public_key": self.public_key,
            "encrypted_private_key": self.encrypted_private_key,
            "created_at": self.created_at,
            "balance": self.balance # Store as native dict/list
        }

        if self._id:
            db.wallets.update_one({"_id": self._id}, {"$set": wallet_data})
        else:
            result = db.wallets.insert_one(wallet_data)
            self._id = result.inserted_id
        
        return self

    @staticmethod
    def find_by_user_id(user_id):
        """Find wallet by user ID"""
        db = get_db()
        try:
            user_id_obj = ObjectId(user_id) if isinstance(user_id, str) else user_id
            data = db.wallets.find_one({"user_id": user_id_obj})
            
            if data:
                return Wallet(
                    _id=data['_id'],
                    user_id=str(data['user_id']),
                    public_key=data['public_key'],
                    encrypted_private_key=data['encrypted_private_key'],
                    created_at=data['created_at'],
                    balance=data.get('balance', {})
                )
        except Exception as e:
            pass
        return None

    @staticmethod
    def find_by_public_key(public_key):
        """Find wallet by public key"""
        db = get_db()
        data = db.wallets.find_one({"public_key": public_key})
        
        if data:
            return Wallet(
                _id=data['_id'],
                user_id=str(data['user_id']),
                public_key=data['public_key'],
                encrypted_private_key=data['encrypted_private_key'],
                created_at=data['created_at'],
                balance=data.get('balance', {})
            )
        return None

    @staticmethod
    def create_wallet_for_user(user_id):
        """Create a new wallet for a user"""
        # Generate a new Solana keypair
        try:
            # Try to use the solana library first
            from solana.keypair import Keypair as SolanaKeypair
            keypair = SolanaKeypair.generate()
            private_key_bytes = keypair.secret_key
            public_key_str = str(keypair.public_key)
        except (ImportError, AttributeError):
            # If solana library doesn't work, try solders
            try:
                from solders.keypair import Keypair as SolderKeypair
                from solders.pubkey import Pubkey
                keypair = SolderKeypair()
                private_key_bytes = bytes(keypair.secret())
                public_key_str = str(keypair.pubkey())
            except (ImportError, AttributeError):
                # If both fail, use a mock implementation
                import secrets
                private_key_bytes = secrets.token_bytes(32)  # 32-byte seed
                # For mock, we'll just create a placeholder public key
                public_key_str = "mock_public_key_" + secrets.token_hex(16)

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
            public_key=public_key_str,
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

    def get_keypair(self):
        """Get the decrypted keypair object for transactions"""
        decrypted_private_key = self.get_private_key()

        try:
            # Try to use the solana library first
            from solana.keypair import Keypair as SolanaKeypair
            # Check if the decrypted key is 64 bytes (full keypair) or 32 bytes (seed)
            if len(decrypted_private_key) == 64:
                return SolanaKeypair.from_secret_key(decrypted_private_key)
            elif len(decrypted_private_key) == 32:
                return SolanaKeypair.from_seed(decrypted_private_key)
        except (ImportError, AttributeError):
            # If solana library doesn't work, try solders
            try:
                from solders.keypair import Keypair as SolderKeypair
                # For solders, we need to handle differently
                if len(decrypted_private_key) == 32:
                    # If it's a 32-byte seed, we need to create keypair differently
                    # solders Keypair constructor can take the private key directly
                    pass  # solders handles this differently
                # For now, return the decrypted key bytes for solders to handle
                return decrypted_private_key
            except (ImportError, AttributeError):
                # If both fail, return the decrypted bytes
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

        db = get_db()
        # Ensure ID is ObjectId
        if not self._id:
             return 

        db.wallets.update_one(
            {"_id": self._id},
            {"$set": {"balance": self.balance}}
        )