"""
TradingBot model for the multi-user Solana trading bot
"""
import sqlite3
from datetime import datetime
import json


class TradingBot:
    def __init__(self, id=None, user_id=None, config=None, is_running=False, created_at=None, updated_at=None):
        self.id = id
        self.user_id = user_id
        self.config = config or {}
        self.is_running = is_running
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()

    @staticmethod
    def create_table():
        """Create the trading_bots table if it doesn't exist"""
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                config TEXT NOT NULL,
                is_running BOOLEAN DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def save(self):
        """Save trading bot to database"""
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        self.updated_at = datetime.utcnow().isoformat()
        
        if self.id:
            cursor.execute('''
                UPDATE trading_bots 
                SET config=?, is_running=?, updated_at=?
                WHERE id=?
            ''', (json.dumps(self.config), self.is_running, self.updated_at, self.id))
        else:
            cursor.execute('''
                INSERT INTO trading_bots (user_id, config, is_running, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (self.user_id, json.dumps(self.config), self.is_running, self.created_at, self.updated_at))
            self.id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return self

    @staticmethod
    def find_by_user_id(user_id):
        """Find trading bot by user ID"""
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM trading_bots WHERE user_id=?', (user_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return TradingBot(
                id=row[0],
                user_id=row[1],
                config=json.loads(row[2]),
                is_running=bool(row[3]),
                created_at=row[4],
                updated_at=row[5]
            )
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
        
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE trading_bots 
            SET config=?, updated_at=?
            WHERE id=?
        ''', (json.dumps(new_config), self.updated_at, self.id))
        
        conn.commit()
        conn.close()

    def set_running_status(self, is_running):
        """Update the running status of the trading bot"""
        self.is_running = is_running
        self.updated_at = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE trading_bots 
            SET is_running=?, updated_at=?
            WHERE id=?
        ''', (is_running, self.updated_at, self.id))
        
        conn.commit()
        conn.close()