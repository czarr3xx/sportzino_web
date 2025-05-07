from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Initialize the database
db = SQLAlchemy()

# User Model for Authentication and Financial Tracking
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # Financial fields
    balance = db.Column(db.Float, default=0.0)
    referral_code = db.Column(db.String(100), unique=True, nullable=False)
    referred_by = db.Column(db.String(100), nullable=True)
    earnings = db.Column(db.Float, default=0.0)
    joined_on = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to Transactions
    transactions = db.relationship('Transaction', backref='user', lazy=True)

# Referral Model
class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    referral_code = db.Column(db.String(100), unique=True, nullable=False)
    image_filename = db.Column(db.String(200), nullable=True)
    referrer_id = db.Column(db.Integer, nullable=True)

# Transaction Model for tracking financial actions
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Float)
    type = db.Column(db.String(50))  # e.g., deposit, freeplay, bonus
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Manual Payment Model
class ManualPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    method = db.Column(db.String(20), nullable=False)
    screenshot_filename = db.Column(db.String(200), nullable=False)
    verified = db.Column(db.Boolean, default=False)
