# database.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    referral_code = db.Column(db.String(50), unique=True)
    referrer_code = db.Column(db.String(50))
    balance = db.Column(db.Float, default=0.0)
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class KYCSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150))
    email = db.Column(db.String(150))
    phone = db.Column(db.String(100))
    country = db.Column(db.String(100))
    wallet_or_ssn = db.Column(db.String(150))
    id_file = db.Column(db.String(255))
    date = db.Column(db.String(100))

class FreeplayEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    referral_code = db.Column(db.String(50))
    reward = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Optional: Additional table if needed
class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False)
