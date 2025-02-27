from app import db
from app.models import User
from flask import current_app
from datetime import datetime, timedelta
from config import Config

def check_trial_expiry_and_notify():
    with current_app.app_context():
        upcoming_trial_expiry = datetime.utcnow() + timedelta(days=1)
        free_users = User.query.filter(
            User.subscription_tier == 'free',
            User.trial_start_date.isnot(None)
        ).all()
        from app.tasks import send_async_email
        for user in free_users:
            trial_end = user.trial_start_date + timedelta(days=Config.SUBSCRIPTION_FREE_TRIAL_DAYS)
            if trial_end.date() <= upcoming_trial_expiry.date():
                try:
                    msg_data = {
                        "subject": "Your Free Trial is Expiring Soon",
                        "recipients": [user.username],
                        "body": (f"Hello {user.username},\n\n"
                                 f"Your free trial will expire on {trial_end.strftime('%Y-%m-%d %H:%M:%S')}.\n"
                                 "Please subscribe to continue enjoying our services.\n\n"
                                 "Thank you!")
                    }
                    send_async_email.delay(msg_data)
                    current_app.logger.info(f"Trial expiry notification queued for {user.username}")
                except Exception as e:
                    current_app.logger.error(f"Failed to queue trial expiry email to {user.username}: {e}")

def check_subscription_expiry_and_notify():
    with current_app.app_context():
        upcoming_subscription_expiry = datetime.utcnow() + timedelta(days=2)
        monthly_users = User.query.filter(
            User.subscription_tier == 'monthly',
            User.subscription_start_date.isnot(None)
        ).all()
        from app.tasks import send_async_email
        for user in monthly_users:
            subscription_end = user.subscription_start_date + timedelta(days=Config.SUBSCRIPTION_MONTHLY_DAYS)
            if subscription_end.date() <= upcoming_subscription_expiry.date():
                try:
                    msg_data = {
                        "subject": "Your Subscription is Expiring Soon",
                        "recipients": [user.username],
                        "body": (f"Hello {user.username},\n\n"
                                 f"Your subscription will expire on {subscription_end.strftime('%Y-%m-%d %H:%M:%S')}.\n"
                                 "Please renew your subscription to continue enjoying our services.\n\n"
                                 "Thank you!")
                    }
                    send_async_email.delay(msg_data)
                    current_app.logger.info(f"Subscription expiry reminder queued for {user.username}")
                except Exception as e:
                    current_app.logger.error(f"Failed to queue subscription expiry email to {user.username}: {e}")
