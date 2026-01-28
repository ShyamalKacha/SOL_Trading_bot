"""
Trade model for the multi-user Solana trading bot
"""
from datetime import datetime
from database import get_db
from bson.objectid import ObjectId

class Trade:
    def __init__(self, id=None, user_id=None, timestamp=None, action=None, token_mint=None, token_symbol=None, price=None, amount=None, pnl=None, network='mainnet', status='completed', _id=None):
        self._id = _id if _id else (ObjectId(id) if id else None)
        self.user_id = user_id
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.action = action
        self.token_mint = token_mint
        self.token_symbol = token_symbol
        self.price = price
        self.amount = amount
        self.pnl = pnl
        self.network = network
        self.status = status

    @property
    def id(self):
        return str(self._id) if self._id else None
        
    @id.setter
    def id(self, value):
        if value:
            self._id = ObjectId(value)
        else:
            self._id = None

    def save(self):
        """Save trade to database"""
        db = get_db()
        
        # Ensure user_id is ObjectId
        user_id_obj = ObjectId(self.user_id) if isinstance(self.user_id, str) else self.user_id
        
        trade_data = {
            "user_id": user_id_obj,
            "timestamp": self.timestamp,
            "action": self.action,
            "token_mint": self.token_mint,
            "token_symbol": self.token_symbol,
            "price": self.price,
            "amount": self.amount,
            "pnl": self.pnl,
            "network": self.network,
            "status": self.status
        }

        if self._id:
            db.trades.update_one({"_id": self._id}, {"$set": trade_data})
        else:
            result = db.trades.insert_one(trade_data)
            self._id = result.inserted_id
        
        return self

    @classmethod
    def find_by_user_and_date(cls, user_id, date_str, network=None):
        """
        Find trades for a user on a specific date and optionally filter by network
        date_str format: YYYY-MM-DD
        """
        db = get_db()
        user_id_obj = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Create date range for query
        start_date = f"{date_str} 00:00:00"
        end_date = f"{date_str} 23:59:59"
        
        query = {
            "user_id": user_id_obj,
            "timestamp": {"$gte": start_date, "$lte": end_date}
        }
        
        if network:
            query["network"] = network
            
        cursor = db.trades.find(query).sort("timestamp", -1) # Sort by newest first
        
        trades = []
        for data in cursor:
            trades.append(cls(
                _id=data['_id'],
                user_id=str(data['user_id']),
                timestamp=data['timestamp'],
                action=data['action'],
                token_mint=data.get('token_mint'),
                token_symbol=data.get('token_symbol'),
                price=data.get('price'),
                amount=data.get('amount'),
                pnl=data.get('pnl'),
                network=data.get('network', 'mainnet'),
                status=data.get('status', 'completed')
            ))
            
        return trades

    @classmethod
    def find_by_user(cls, user_id, page=1, per_page=15, network=None, date=None):
        """
        Find trades for a user with pagination
        """
        db = get_db()
        user_id_obj = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        query = {"user_id": user_id_obj}
        
        if network:
            query["network"] = network
            
        if date:
            # Timestamp is stored as string "YYYY-MM-DD HH:MM:SS"
            # We want to match strings starting with the date
            query["timestamp"] = {"$regex": f"^{date}"}
            
        # Get total count for pagination
        total_count = db.trades.count_documents(query)
        
        # Calculate skip
        skip = (page - 1) * per_page
        
        cursor = db.trades.find(query).sort("timestamp", -1).skip(skip).limit(per_page)
        
        trades = []
        for data in cursor:
            trades.append(cls(
                _id=data['_id'],
                user_id=str(data['user_id']),
                timestamp=data['timestamp'],
                action=data['action'],
                token_mint=data.get('token_mint'),
                token_symbol=data.get('token_symbol'),
                price=data.get('price'),
                amount=data.get('amount'),
                pnl=data.get('pnl'),
                network=data.get('network', 'mainnet'),
                status=data.get('status', 'completed')
            ))
            
        return trades, total_count
