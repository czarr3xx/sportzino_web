import string
import random
from flask import Flask, request, redirect, url_for
from models import db, User

app = Flask(__name__)

def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

@app.route('/register', methods=['POST'])
def register():
    email = request.form['email']
    referred_by = request.form.get('referral_code')

    new_user = User(
        email=email,
        referral_code=generate_referral_code(),
        referred_by=referred_by
    )

    db.session.add(new_user)
    db.session.commit()

    # Give bonus to referrer
    if referred_by:
        referrer = User.query.filter_by(referral_code=referred_by).first()
        if referrer:
            referrer.earnings += 82  # Assume fixed $82 for now
            db.session.commit()

    return redirect(url_for('index'))
