"""
User model for the multi-user Solana trading bot
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
from cryptography.fernet import Fernet
import json
from database import get_db
from bson.objectid import ObjectId

class User:
    def __init__(self, id=None, email=None, password_hash=None, created_at=None, is_active=True, _id=None):
        self._id = _id if _id else (ObjectId(id) if id else None)
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.is_active = is_active

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
        """Create the users table if it doesn't exist"""
        # MongoDB creates collections implicitly. Indexes are handled in database.py
        pass

    def save(self):
        """Save user to database"""
        db = get_db()
        
        user_data = {
            "email": self.email,
            "password_hash": self.password_hash,
            "created_at": self.created_at,
            "is_active": self.is_active
        }

        if self._id:
            db.users.update_one({"_id": self._id}, {"$set": user_data})
        else:
            result = db.users.insert_one(user_data)
            self._id = result.inserted_id
        
        return self

    @staticmethod
    def find_by_email(email):
        """Find user by email"""
        db = get_db()
        data = db.users.find_one({"email": email})
        
        if data:
            return User(
                _id=data['_id'],
                email=data['email'],
                password_hash=data['password_hash'],
                created_at=data['created_at'],
                is_active=data.get('is_active', True)
            )
        return None

    @staticmethod
    def find_by_id(user_id):
        """Find user by ID"""
        db = get_db()
        try:
            data = db.users.find_one({"_id": ObjectId(user_id)})
            
            if data:
                return User(
                    _id=data['_id'],
                    email=data['email'],
                    password_hash=data['password_hash'],
                    created_at=data['created_at'],
                    is_active=data.get('is_active', True)
                )
        except Exception:
            pass
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
        db = get_db()
        db.users.update_one(
            {"email": email},
            {"$set": {"otp_secret": otp_secret, "otp_expiry": expiry.isoformat()}}
        )

    @staticmethod
    def verify_otp(email, otp_secret):
        """Verify OTP secret for email verification"""
        db = get_db()
        user = db.users.find_one({"email": email})
        
        if user and user.get('otp_secret') == otp_secret:
            # Check if OTP is expired
            from datetime import datetime
            
            expiry_str = user.get('otp_expiry')
            if expiry_str:
                expiry = datetime.fromisoformat(expiry_str)
                if expiry > datetime.utcnow():
                    # Clear OTP after successful verification
                    db.users.update_one(
                        {"email": email},
                        {"$unset": {"otp_secret": "", "otp_expiry": ""}}
                    )
                    return True
        return False