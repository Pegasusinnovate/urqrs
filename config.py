import os
import secrets

class Config:
    # Critical: use a secure secret key (override with an env variable in production)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-default-secret-key')
    
    # SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Base directory and file storage paths
    BASE_DIR = os.getcwd()
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MENU_FOLDER = os.path.join(BASE_DIR, 'menus')
    GALLERY_FOLDER = os.path.join(BASE_DIR, 'static', 'gallery')
    
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB upload limit
    ALLOWED_MENU_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
    ALLOWED_GALLERY_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

    # Subscription durations (in days)
    SUBSCRIPTION_FREE_TRIAL_DAYS = 7
    SUBSCRIPTION_MONTHLY_DAYS = 30

    # Razorpay Configuration (set your production keys via environment variables)
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_3dlpA7ZXXLKAdg')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'vxH7O4GdDKV3P8MGKBfjeG1D')
    RAZORPAY_MODE = os.environ.get('RAZORPAY_MODE', 'production')

    # Flask-Mail Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.example.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'your-email@example.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'your-email-password')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@example.com')

    # APScheduler Configuration
    SCHEDULER_API_ENABLED = True

    # Google OAuth Configuration (set production keys via environment variables)
    GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '') 
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '')

                                                
