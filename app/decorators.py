# app/decorators.py
from functools import wraps
from flask import flash, redirect, url_for, request
from flask_login import current_user
from app.utils import is_subscription_valid  # Use the centralized function

def subscription_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not is_subscription_valid(current_user):
            flash("Your subscription has expired or is not active. Please renew your subscription to access this feature.", "warning")
            return redirect(url_for("subscription.subscription_status", next=request.url))
        return func(*args, **kwargs)
    return wrapper