"""
TradingBot model for the multi-user Solana trading bot
"""
from datetime import datetime
import json
from database import get_db
from bson.objectid import ObjectId

class TradingBot:
    def __init__(self, id=None, user_id=None, config=None, is_running=False, created_at=None, updated_at=None, _id=None):
        self._id = _id if _id else (ObjectId(id) if id else None)
        self.user_id = user_id
        self.config = config or {}
        self.is_running = is_running
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()

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
        """Create the trading_bots table if it doesn't exist"""
        pass

    def save(self):
        """Save trading bot to database"""
        db = get_db()
        
        self.updated_at = datetime.utcnow().isoformat()
        
        # Ensure user_id is ObjectId
        user_id_obj = ObjectId(self.user_id) if isinstance(self.user_id, str) else self.user_id
        
        bot_data = {
            "user_id": user_id_obj,
            "config": self.config, # Store as native dict
            "is_running": self.is_running,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

        if self._id:
            db.trading_bots.update_one({"_id": self._id}, {"$set": bot_data})
        else:
            result = db.trading_bots.insert_one(bot_data)
            self._id = result.inserted_id
        
        return self

    @staticmethod
    def find_by_user_id(user_id):
        """Find trading bot by user ID"""
        db = get_db()
        try:
            user_id_obj = ObjectId(user_id) if isinstance(user_id, str) else user_id
            data = db.trading_bots.find_one({"user_id": user_id_obj})
            
            if data:
                return TradingBot(
                    _id=data['_id'],
                    user_id=str(data['user_id']),
                    config=data.get('config', {}),
                    is_running=data.get('is_running', False),
                    created_at=data['created_at'],
                    updated_at=data['updated_at']
                )
        except Exception:
            pass
        return None

    @staticmethod
    def create_bot_for_user(user_id):
        """Create a new trading bot for a user with default config"""
        bot = TradingBot(
            user_id=user_id,
            config={
                'up_percentage': 5.0,
                'down_percentage': 3.0,
                'selected_token': 'So11111111111111111111111111111111111111112',  # SOL
                'trade_amount': 10.0,
                'parts': 1,
                'network': 'mainnet',
                'trading_mode': 'automatic'
            }
        )
        
        return bot.save()

    def update_config(self, new_config):
        """Update trading bot configuration"""
        self.config = new_config
        self.updated_at = datetime.utcnow().isoformat()
        
        db = get_db()
        if not self._id:
            return

        db.trading_bots.update_one(
            {"_id": self._id},
            {"$set": {"config": self.config, "updated_at": self.updated_at}}
        )

    def set_running_status(self, is_running):
        """Update the running status of the trading bot"""
        self.is_running = is_running
        self.updated_at = datetime.utcnow().isoformat()
        
        db = get_db()
        if not self._id:
            return

        db.trading_bots.update_one(
            {"_id": self._id},
            {"$set": {"is_running": self.is_running, "updated_at": self.updated_at}}
        )