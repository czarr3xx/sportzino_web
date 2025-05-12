import string
import random
from flask import Flask, request, redirect, url_for, render_template
from models import db, User

app = Flask(__name__)

# Function to generate a random 8-character referral code
def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Route to render the index page
@app.route('/')
def index():
    return render_template('index.html')

# Route for user registration
@app.route('/register', methods=['POST'])
def register():
    # Get form data from the registration form
    email = request.form['email']
    referred_by = request.form.get('referral_code')

    # Create a new user with the referral code
    new_user = User(
        email=email,
        referral_code=generate_referral_code(),
        referred_by=referred_by
    )

    # Add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    # If the user was referred, give the referrer a bonus
    if referred_by:
        referrer = User.query.filter_by(referral_code=referred_by).first()
        if referrer:
            referrer.earnings += 82  # Assume fixed $82 for now
            db.session.commit()

    # Redirect to the index page after registration
    return redirect(url_for('index'))
