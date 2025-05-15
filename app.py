from flask import Flask, request, jsonify, render_template, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_cors import CORS
import os
import csv
import stripe
import paypalrestsdk
from io import StringIO
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from waitress import serve
from datetime import datetime

# Load environment variables
load_dotenv()

# Flask App Config
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///referrals.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)

# Stripe & PayPal Config
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
paypalrestsdk.configure({
    "mode": "sandbox",
    "client_id": os.getenv('PAYPAL_CLIENT_ID'),
    "client_secret": os.getenv('PAYPAL_CLIENT_SECRET')
})

# Initialize DB & Auth
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('freeplay'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error="Email already registered.")
        user = User(email=email)
        user.set_password(password)
        user.referral_code = email.split('@')[0] + str(int(datetime.utcnow().timestamp()))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('freeplay'))
    return render_template('register.html')

@app.route('/freeplay')
@login_required
def freeplay():
    return render_template('freeplay.html', background_music_url=url_for('static', filename='music/bg.mp3'))

# API Routes
@app.route('/api/user-info')
@login_required
def user_info():
    return jsonify({
        "balance": current_user.balance,
        "referral_link": f"https://example.com/referral/{current_user.referral_code}"
    })

@app.route('/api/leaderboard')
def get_leaderboard():
    entries = FreeplayEntry.query.order_by(FreeplayEntry.reward.desc()).limit(10).all()
    leaderboard = [
        {
            "user_id": e.user_id,
            "referral_code": e.referral_code,
            "amount": e.reward,
            "timestamp": e.timestamp.strftime('%Y-%m-%d %H:%M')
        } for e in entries
    ]
    return jsonify({"leaderboard": leaderboard})

@app.route('/api/freeplay', methods=['POST'])
@login_required
def freeplay_api():
    data = request.get_json() or {}
    code = data.get('referral_code')
    if not code:
        return jsonify({"error": "Please enter a referral code"}), 400
    reward = 10.0
    entry = FreeplayEntry(user_id=current_user.id, referral_code=code, reward=reward)
    db.session.add(entry)
    current_user.balance += reward
    db.session.commit()
    return jsonify({"message": "Referral recorded. $10 reward added."}), 200

@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.get_json() or {}
    return jsonify({"message": "Form submitted successfully"}), 200

@app.route('/api/admin-dashboard')
@login_required
def admin_dashboard():
    if current_user.email != os.getenv('ADMIN_EMAIL'):
        return jsonify({"error": "Unauthorized"}), 403
    subs = KYCSubmission.query.all()
    users = User.query.all()
    return jsonify({
        "submissions": [{
            "id": s.id,
            "full_name": s.full_name,
            "email": s.email,
            "phone": s.phone,
            "country": s.country,
            "wallet_or_ssn": s.wallet_or_ssn,
            "id_file": s.id_file,
            "date": s.date
        } for s in subs],
        "users": [{
            "id": u.id,
            "email": u.email,
            "balance": u.balance,
            "referral_code": u.referral_code
        } for u in users]
    })

@app.route('/api/download-kyc-csv')
@login_required
def download_kyc_csv():
    if current_user.email != os.getenv('ADMIN_EMAIL'):
        return jsonify({"error": "Unauthorized"}), 403
    subs = KYCSubmission.query.all()
    si = StringIO()
    w = csv.writer(si)
    w.writerow(['ID', 'Full Name', 'Email', 'Phone', 'Country', 'Wallet/SSN', 'ID File', 'Date'])
    for s in subs:
        w.writerow([s.id, s.full_name, s.email, s.phone, s.country, s.wallet_or_ssn, s.id_file, s.date])
    resp = Response(si.getvalue(), mimetype='text/csv')
    resp.headers['Content-Disposition'] = 'attachment; filename=submissions.csv'
    return resp

# Stripe & PayPal
@app.route('/api/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': 'Sportzino Membership'},
                    'unit_amount': 1000,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='https://sportzino.com/success',
            cancel_url='https://sportzino.com/cancel',
        )
        return jsonify({"url": checkout_session.url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/paypal-pay', methods=['POST'])
def paypal_pay():
    data = request.get_json() or {}
    payment = paypalrestsdk.Payment(data)
    if payment.create():
        link = next((l.href for l in payment.links if l.method == 'REDIRECT'), None)
        return jsonify({"url": link}), 200
    return jsonify({"error": "PayPal error"}), 500

@app.route('/api/chime-pay', methods=['POST'])
def chime_pay():
    return jsonify({"message": "Transfer manually to Chime Bank."}), 200

# Error Handlers
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('500.html'), 500

# Run App
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    if os.getenv('FLASK_ENV') == 'production':
        serve(app, host='0.0.0.0', port=5000)
    else:
        app.run(debug=True)
