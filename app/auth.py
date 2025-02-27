import re
import random
from flask import (
    Blueprint, render_template, redirect, url_for, request, flash,
    session, current_app
)
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager
from app.models import User
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from config import Config
from flask_dance.contrib.google import google
from urllib.parse import urlparse
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError

auth = Blueprint('auth', __name__)

def is_valid_email(email):
    pattern = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    return re.match(pattern, email) is not None

def is_strong_password(password):
    """
    Enforces a password policy:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}$'
    return re.match(pattern, password)

def generate_otp():
    return str(random.randint(100000, 999999))

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('username')
        password = request.form.get('password')
        display_name = request.form.get('display_name')
        if not is_valid_email(email):
            flash('Please enter a valid email address.', 'danger')
            return redirect(url_for('auth.signup'))
        if User.query.filter_by(username=email).first():
            flash('Email already exists. Please choose a different one.', 'danger')
            return redirect(url_for('auth.signup'))
        if not is_strong_password(password):
            flash('Password must be at least 8 characters long and include an uppercase letter, a lowercase letter, a digit, and a special character.', 'danger')
            return redirect(url_for('auth.signup'))
        otp = generate_otp()
        session['signup_data'] = {
            'email': email,
            'password': password,
            'display_name': display_name,
            'otp': otp
        }
        flash(f"Your OTP is: {otp} (In production, this will be sent securely)", "info")
        return redirect(url_for('auth.verify_otp'))
    return render_template('signup.html', title="Sign Up")

@auth.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    signup_data = session.get('signup_data')
    if not signup_data:
        flash("No signup data found. Please sign up again.", "danger")
        return redirect(url_for('auth.signup'))
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        if entered_otp == signup_data.get('otp'):
            new_user = User(
                username=signup_data.get('email'),
                display_name=signup_data.get('display_name'),
                password_hash=generate_password_hash(signup_data.get('password'), method='pbkdf2:sha256'),
                trial_start_date=datetime.utcnow()
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            session.pop('signup_data', None)
            flash("Signup successful and OTP verified!", "success")
            return redirect(url_for('menu.dashboard'))
        else:
            flash("Incorrect OTP. Please try again.", "danger")
            return redirect(url_for('auth.verify_otp'))
    return render_template('verify_otp.html', title="Verify OTP")

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid credentials', 'danger')
            return redirect(url_for('auth.login'))
        login_user(user)
        next_page = request.args.get("next")
        if not next_page or urlparse(next_page).netloc != "":
            next_page = url_for('menu.dashboard')
        return redirect(next_page)
    return render_template('login.html', title="Log In")

@auth.route('/login/google')
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login", next=request.args.get("next")))
    try:
        resp = google.get("/oauth2/v2/userinfo")
    except TokenExpiredError:
        del google.token
        flash("Google session expired. Please log in again.", "warning")
        return redirect(url_for("google.login", next=request.args.get("next")))
    if not resp.ok:
        flash("Failed to fetch user info from Google.", "danger")
        return redirect(url_for("auth.login"))
    user_info = resp.json()
    email = user_info.get("email")
    display_name = user_info.get("name")
    if not email:
        flash("Google account does not have an email address.", "danger")
        return redirect(url_for("auth.login"))
    user = User.query.filter_by(username=email).first()
    if not user:
        user = User(
            username=email,
            display_name=display_name,
            password_hash=generate_password_hash("google_oauth_dummy", method='pbkdf2:sha256'),
            trial_start_date=datetime.utcnow()
        )
        db.session.add(user)
        db.session.commit()
    login_user(user)
    flash("Logged in with Google.", "success")
    next_page = request.args.get("next")
    if not next_page or urlparse(next_page).netloc != "":
        next_page = url_for('menu.dashboard')
    return redirect(next_page)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/update_profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    if request.method == 'POST':
        new_display_name = request.form.get('display_name')
        if new_display_name:
            current_user.display_name = new_display_name
            db.session.commit()
            flash("Profile updated successfully.", "success")
            return redirect(url_for('menu.dashboard'))
        else:
            flash("Please enter a valid display name.", "danger")
            return redirect(url_for('auth.update_profile'))
    return render_template('update_profile.html', title="Update Profile")

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))
