import string
import random
from flask import Flask, request, redirect, url_for, render_template, flash
from werkzeug.security import generate_password_hash
from models import db, User
from flask_login import LoginManager

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Make sure to replace with a secure one in production

login_manager = LoginManager(app)

# Generate an 8-character referral code
def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    full_name = request.form['full_name']
    email = request.form['email']
    password = request.form['password']
    referred_by = request.form.get('referral_code')

    # Check if the user already exists
    if User.query.filter_by(email=email).first():
        flash('Email already registered. Please log in or use a different email.')
        return redirect(url_for('index'))

    # Create hashed password
    hashed_password = generate_password_hash(password)

    # Create new user
    new_user = User(
        full_name=full_name,
        email=email,
        password=hashed_password,
        referral_code=generate_referral_code(),
        referred_by=referred_by
    )

    db.session.add(new_user)
    db.session.commit()

    # Reward the referrer
    if referred_by:
        referrer = User.query.filter_by(referral_code=referred_by).first()
        if referrer:
            referrer.earnings += 82.0  # or whatever amount
            db.session.commit()

    flash('Registration successful!')
    return redirect(url_for('index'))
