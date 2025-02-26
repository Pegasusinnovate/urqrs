from app import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)  # Email
    display_name = db.Column(db.String(150), nullable=True)  # New field for display name
    password_hash = db.Column(db.String(200), nullable=False)
    default_menu = db.Column(db.String(10), nullable=False, default='file')
    
    # Subscription fields
    subscription_tier = db.Column(db.String(20), nullable=False, default='free')  # "free" or "monthly"
    trial_start_date = db.Column(db.DateTime(), nullable=True)
    subscription_start_date = db.Column(db.DateTime(), nullable=True)
    subscription_status = db.Column(db.String(20), nullable=False, default='inactive')  # "active" or "inactive"
    razorpay_payment_id = db.Column(db.String(100), nullable=True)
    
    # Relationships for simple menu and gallery
    simple_menu = db.relationship('SimpleMenu', backref='user', uselist=False, cascade="all, delete-orphan")
    gallery = db.relationship('Gallery', backref='user', uselist=False, cascade="all, delete-orphan")

class SimpleMenu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    menu_title = db.Column(db.String(200), nullable=False)
    dishes = db.Column(db.JSON, nullable=False)

class Gallery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    items = db.Column(db.JSON, nullable=True)