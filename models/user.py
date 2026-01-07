"""
User model for the multi-user Solana trading bot
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from cryptography.fernet import Fernet
import json


class User:
    def __init__(self, id=None, email=None, password_hash=None, created_at=None, is_active=True):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.is_active = is_active

    @staticmethod
    def create_table():
        """Create the users table if it doesn't exist"""
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                otp_secret TEXT,
                otp_expiry TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    def save(self):
        """Save user to database"""
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        if self.id:
            cursor.execute('''
                UPDATE users 
                SET email=?, password_hash=?, is_active=?
                WHERE id=?
            ''', (self.email, self.password_hash, self.is_active, self.id))
        else:
            cursor.execute('''
                INSERT INTO users (email, password_hash, created_at, is_active)
                VALUES (?, ?, ?, ?)
            ''', (self.email, self.password_hash, self.created_at, self.is_active))
            self.id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return self

    @staticmethod
    def find_by_email(email):
        """Find user by email"""
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE email=?', (email,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return User(
                id=row[0],
                email=row[1],
                password_hash=row[2],
                created_at=row[3],
                is_active=bool(row[4])
            )
        return None

    @staticmethod
    def find_by_id(user_id):
        """Find user by ID"""
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE id=?', (user_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return User(
                id=row[0],
                email=row[1],
                password_hash=row[2],
                created_at=row[3],
                is_active=bool(row[4])
            )
        return None

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def set_otp_secret(email, otp_secret, expiry):
        """Set OTP secret for email verification"""
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET otp_secret=?, otp_expiry=?
            WHERE email=?
        ''', (otp_secret, expiry.isoformat(), email))
        
        conn.commit()
        conn.close()

    @staticmethod
    def verify_otp(email, otp_secret):
        """Verify OTP secret for email verification"""
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT otp_secret, otp_expiry FROM users 
            WHERE email=?
        ''', (email,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row and row[0] == otp_secret:
            # Check if OTP is expired
            from datetime import datetime
            expiry = datetime.fromisoformat(row[1])
            if expiry > datetime.utcnow():
                # Clear OTP after successful verification
                cursor = sqlite3.connect('trading_bot.db').cursor()
                cursor.execute('UPDATE users SET otp_secret=NULL, otp_expiry=NULL WHERE email=?', (email,))
                cursor.connection.commit()
                cursor.connection.close()
                return True
        return False