import os
import os.path

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-default-secret-key')  # Change for production!
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    BASE_DIR = os.getcwd()
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MENU_FOLDER = os.path.join(BASE_DIR, 'menus')
    GALLERY_FOLDER = os.path.join(BASE_DIR, 'static', 'gallery')
    
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_MENU_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
    ALLOWED_GALLERY_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

    SUBSCRIPTION_FREE_TRIAL_DAYS = 7
    SUBSCRIPTION_MONTHLY_DAYS = 30

    # Subscription price in paise (e.g., 1100 paise = Rs.11.00)
    SUBSCRIPTION_PRICE = int(os.environ.get('SUBSCRIPTION_PRICE', 1100))

    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_3dlpA7ZXXLKAdg')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'vxH7O4GdDKV3P8MGKBfjeG1D')
    RAZORPAY_MODE = os.environ.get('RAZORPAY_MODE', 'production')

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.example.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'your-email@example.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'your-email-password')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@example.com')

    SCHEDULER_API_ENABLED = True

    GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '') 
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '')

    FIREBASE_BUCKET = os.environ.get('FIREBASE_BUCKET', 'your-project-id.appspot.com')
