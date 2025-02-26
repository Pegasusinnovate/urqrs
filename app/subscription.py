import os
import razorpay
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from app import db
from app.models import User
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from config import Config
import logging
from app.utils import is_subscription_valid

logger = logging.getLogger(__name__)

RAZORPAY_KEY_ID = Config.RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET = Config.RAZORPAY_KEY_SECRET

subscription = Blueprint('subscription', __name__)

@subscription.route('/subscription')
@login_required
def subscription_status():
    now = datetime.utcnow()
    trial_end = None
    if current_user.trial_start_date:
        trial_end = current_user.trial_start_date + timedelta(days=Config.SUBSCRIPTION_FREE_TRIAL_DAYS)
    subscription_expiry = None
    if current_user.subscription_start_date:
        subscription_expiry = current_user.subscription_start_date + timedelta(days=Config.SUBSCRIPTION_MONTHLY_DAYS)
    return render_template('subscription_status.html',
                           user=current_user,
                           now=now,
                           trial_end=trial_end,
                           subscription_expiry=subscription_expiry)

@subscription.route('/subscribe', methods=['POST'])
@login_required
def subscribe():
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    try:
        order_amount = 1100  # Rs. 11.00 in paise
        order_currency = "INR"
        order_receipt = f"order_rcptid_{current_user.id}_{datetime.utcnow().timestamp()}"
        razorpay_order = client.order.create({
            "amount": order_amount,
            "currency": order_currency,
            "receipt": order_receipt,
            "payment_capture": 1  # auto-capture payment
        })
        logger.debug("Razorpay order created: %s", razorpay_order)
        # Render unified checkout template.
        return render_template("checkout.html", order=razorpay_order, user=current_user)
    except Exception as e:
        logger.error("Razorpay order creation failed: %s", e)
        flash("An error occurred while processing your subscription. Please try again.", "danger")
        return redirect(url_for('subscription.subscription_status'))

@subscription.route('/subscription/verify', methods=['POST'])
@login_required
def verify_subscription():
    logger.debug("Verify subscription POST data: %s", dict(request.form))
    params_dict = {
        "razorpay_order_id": request.form.get("razorpay_order_id"),
        "razorpay_payment_id": request.form.get("razorpay_payment_id"),
        "razorpay_signature": request.form.get("razorpay_signature")
    }
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    try:
        client.utility.verify_payment_signature(params_dict)
        logger.debug("Signature verification successful for: %s", params_dict)
        
        now = datetime.utcnow()
        trial_end = None
        if current_user.trial_start_date:
            trial_end = current_user.trial_start_date + timedelta(days=Config.SUBSCRIPTION_FREE_TRIAL_DAYS)
        
        if trial_end and now > trial_end:
            if current_user.simple_menu:
                menu_file = os.path.join(current_app.config['MENU_FOLDER'], f"simple_menu_{current_user.id}.html")
                if os.path.exists(menu_file):
                    try:
                        os.remove(menu_file)
                        logger.debug("Deleted simple menu file: %s", menu_file)
                    except Exception as e:
                        logger.error("Error deleting simple menu file %s: %s", menu_file, e)
                db.session.delete(current_user.simple_menu)
            if current_user.gallery:
                for filename in (current_user.gallery.items or []):
                    gallery_file = os.path.join(current_app.config['GALLERY_FOLDER'], filename)
                    if os.path.exists(gallery_file):
                        try:
                            os.remove(gallery_file)
                            logger.debug("Deleted gallery file: %s", gallery_file)
                        except Exception as e:
                            logger.error("Error deleting gallery file %s: %s", gallery_file, e)
                db.session.delete(current_user.gallery)
            logger.debug("Free trial data cleared because trial ended at %s", trial_end)
        else:
            logger.debug("User upgraded during trial period; retaining trial data.")
        
        current_user.subscription_tier = "monthly"
        current_user.subscription_start_date = now
        current_user.subscription_status = "active"
        current_user.razorpay_payment_id = params_dict["razorpay_payment_id"]
        db.session.commit()
        logger.debug("User subscription updated: %s", current_user)
        flash("Subscription activated! Enjoy your monthly plan.", "success")
        return redirect(url_for('subscription.subscription_status'))
    except razorpay.errors.SignatureVerificationError as e:
        logger.error("Signature verification failed: %s", e)
        flash("Payment verification failed. Please try again.", "danger")
        return redirect(url_for('subscription.subscription_status'))
    except Exception as e:
        logger.error("Error during payment verification: %s", e)
        flash("An unexpected error occurred. Please try again.", "danger")
        return redirect(url_for('subscription.subscription_status'))

@subscription.route('/cancel_subscription')
@login_required
def cancel_subscription():
    if current_user.subscription_tier == "monthly" and current_user.subscription_status == "active":
        current_user.subscription_status = "cancelled"
        db.session.commit()
        flash("Your subscription has been cancelled. You can use our facilities until the current subscription period ends.", "info")
    else:
        flash("No active subscription to cancel.", "warning")
    return redirect(url_for('subscription.subscription_status'))

@subscription.route('/check_expired')
def check_expired():
    from app.models import User
    expired_users = User.query.filter(
        User.subscription_tier == "free",
        User.trial_start_date < datetime.utcnow() - timedelta(days=Config.SUBSCRIPTION_FREE_TRIAL_DAYS)
    ).all()
    for user in expired_users:
        if user.simple_menu:
            menu_file = os.path.join(current_app.config['MENU_FOLDER'], f"simple_menu_{user.id}.html")
            if os.path.exists(menu_file):
                try:
                    os.remove(menu_file)
                    current_app.logger.info("Deleted expired simple menu file: %s", menu_file)
                except Exception as e:
                    current_app.logger.error("Error deleting expired simple menu file %s: %s", menu_file, e)
            db.session.delete(user.simple_menu)
        if user.gallery:
            for filename in (user.gallery.items or []):
                gallery_file = os.path.join(current_app.config['GALLERY_FOLDER'], filename)
                if os.path.exists(gallery_file):
                    try:
                        os.remove(gallery_file)
                        current_app.logger.info("Deleted expired gallery file: %s", gallery_file)
                    except Exception as e:
                        current_app.logger.error("Error deleting expired gallery file %s: %s", gallery_file, e)
            db.session.delete(user.gallery)
    db.session.commit()
    return "Expired free trial data and files cleaned up", 200