from flask import Flask, request, jsonify, Response
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

# Load environment variables
load_dotenv()

# Flask App Config
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///referrals.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)  # Enable CORS

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
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())  # Added for timestamp

    def set_password(self, password):
        """Hashes the user's password."""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Checks if the provided password matches the hashed password."""
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Public API Routes
@app.route('/api/user-info', methods=['GET'])
@login_required
def user_info():
    return jsonify({
        "balance": current_user.balance,
        "referral_link": f"https://example.com/referral/{current_user.referral_code}"
    })

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    data = [
        {"country": "US", "name": "Micheal Sawyer", "amount": 120.50},
        {"country": "US", "name": "Jane Smith", "amount": 100.25},
    ]
    return jsonify({"leaderboard": data})

@app.route('/api/freeplay', methods=['POST'])
def freeplay():
    data = request.get_json() or {}
    code = data.get('referral_code')
    if not code:
        return jsonify({"error": "Please enter a referral code"}), 400
    return jsonify({"message": f"Received referral code: {code}"}), 200

@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.get_json() or {}  # extract fields
    # save to db if needed
    return jsonify({"message": "Form submitted successfully"}), 200

# Admin API Routes
@app.route('/api/admin-dashboard', methods=['GET'])
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

@app.route('/api/download-kyc-csv', methods=['GET'])
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

# Payment API Routes
@app.route('/api/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        sess = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': 'Sportzino Membership'},
                    'unit_amount': 1000
                },
                'quantity': 1
            }],
            mode='payment',
            success_url='https://sportzino.com/success',  # Ensure proper URL for success
            cancel_url='https://sportzino.com/cancel'   # Ensure proper URL for cancel
        )
        return jsonify({"url": sess.url}), 200
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

# Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables (For production, use migrations)
    app.run(debug=True)
