# -------------------- Imports --------------------
import os
import csv
import stripe
import paypalrestsdk
from io import StringIO
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# -------------------- Load Environment --------------------
load_dotenv()

# -------------------- Flask App Config --------------------
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///referrals.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# -------------------- Extensions Init --------------------
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# -------------------- Stripe Config --------------------
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# -------------------- PayPal Config --------------------
paypalrestsdk.configure({
    "mode": "sandbox",  # Change to "live" for production
    "client_id": os.getenv('PAYPAL_CLIENT_ID'),
    "client_secret": os.getenv('PAYPAL_CLIENT_SECRET')
})

# -------------------- Models --------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    referral_code = db.Column(db.String(50), unique=True)
    referrer_code = db.Column(db.String(50))
    balance = db.Column(db.Float, default=0.0)

class KYCSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150))
    email = db.Column(db.String(150))
    phone = db.Column(db.String(100))
    country = db.Column(db.String(100))
    wallet_or_ssn = db.Column(db.String(150))
    id_file = db.Column(db.String(255))
    date = db.Column(db.String(100))

# -------------------- Login Manager --------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------- Routes: Public --------------------
@app.route('/')
def index():
    balance = 50.75
    referral_link = "https://example.com/referral/12345"
    leaderboard = [
        {"country": "US", "name": "John Doe", "amount": 120.50},
        {"country": "US", "name": "Jane Smith", "amount": 100.25},
    ]
    return render_template("index.html", balance=balance, referral_link=referral_link, leaderboard=leaderboard)

@app.route('/freeplay', methods=['GET', 'POST'])
def freeplay():
    if request.method == 'POST':
        referral_code = request.form.get('referral_code')
        if referral_code:
            flash(f"Received referral code: {referral_code}", "info")
        else:
            flash("Please enter a referral code", "warning")
    return render_template('freeplay.html')

@app.route('/submit', methods=['POST'])
def submit():
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    country = request.form.get('country')
    wallet_or_ssn = request.form.get('wallet_or_ssn')
    flash('Form submitted successfully!', 'success')
    return redirect(url_for('index'))

# -------------------- Routes: Admin Dashboard --------------------
@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    if current_user.email != os.getenv('ADMIN_EMAIL'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('index'))

    submissions = KYCSubmission.query.all()
    users = User.query.all()
    return render_template("admin_dashboard.html", submissions=submissions, users=users)

@app.route('/download-kyc-csv')
@login_required
def download_kyc_csv():
    if current_user.email != os.getenv('ADMIN_EMAIL'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('index'))

    submissions = KYCSubmission.query.all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Full Name', 'Email', 'Phone', 'Country', 'Wallet/SSN', 'ID File', 'Date'])
    for sub in submissions:
        writer.writerow([sub.id, sub.full_name, sub.email, sub.phone, sub.country, sub.wallet_or_ssn, sub.id_file, sub.date])

    output = Response(si.getvalue(), mimetype='text/csv')
    output.headers["Content-Disposition"] = "attachment; filename=kyc_submissions.csv"
    return output

# -------------------- Routes: Payment --------------------
@app.route('/pay')
def pay():
    return render_template('payment.html')

@app.route('/create-checkout-session', methods=['POST'])
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
            success_url='https://sportzino.com/',
            cancel_url=url_for('pay', _external=True),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('pay'))

@app.route('/paypal-pay', methods=['POST'])
def paypal_pay():
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {"payment_method": "paypal"},
        "redirect_urls": {
            "return_url": "https://sportzino.com/",
            "cancel_url": url_for('pay', _external=True)
        },
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": "Sportzino Membership",
                    "sku": "001",
                    "price": "10.00",
                    "currency": "USD",
                    "quantity": 1
                }]
            },
            "amount": {"total": "10.00", "currency": "USD"},
            "description": "Payment for Sportzino Membership"
        }]
    })

    if payment.create():
        for link in payment.links:
            if link.method == "REDIRECT":
                return redirect(link.href)
    flash('Error creating PayPal payment', 'danger')
    return redirect(url_for('pay'))

@app.route('/chime-pay', methods=['POST'])
def chime_pay():
    flash('Please transfer manually to Chime Bank. After confirmation, access is granted.', 'success')
    return redirect("https://sportzino.com/")

# -------------------- Run Flask App --------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
