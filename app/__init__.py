import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from config import Config
from flask_migrate import Migrate
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask_caching import Cache
from flask_mail import Mail
from flask_apscheduler import APScheduler

# Initialize core extensions
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()
cache = Cache(config={'CACHE_TYPE': 'simple'})
mail = Mail()
scheduler = APScheduler()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Sentry for error monitoring
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN', ''),
        integrations=[FlaskIntegration()],
        traces_sample_rate=1.0,
        environment=os.environ.get('FLASK_ENV', 'development')
    )

    # Create required folders if they don't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['MENU_FOLDER'], exist_ok=True)
    os.makedirs(app.config['GALLERY_FOLDER'], exist_ok=True)

    # Initialize extensions with the app instance
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    mail.init_app(app)

    # Only start the scheduler if not running as a Celery worker.
    if not os.environ.get('CELERY_WORKER'):
        scheduler.init_app(app)
        scheduler.start()

    login_manager.login_view = 'auth.login'

    # Setup logging to file
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10, delay=True)
    file_handler.setFormatter(logging.Formatter(
         '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('App startup')

    # Register blueprints for different functionalities
    from app.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    
    from app.menu import menu as menu_blueprint
    app.register_blueprint(menu_blueprint)
    
    from app.gallery import gallery as gallery_blueprint
    app.register_blueprint(gallery_blueprint)
    
    from app.subscription import subscription as subscription_blueprint
    app.register_blueprint(subscription_blueprint)
    
    # Register main blueprint for public routes (e.g., the front page)
    from app.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Register Google OAuth blueprint using Flask-Dance with updated scopes.
    from flask_dance.contrib.google import make_google_blueprint
    google_bp = make_google_blueprint(
    client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
    client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ],
    redirect_url="/google_login/authorized"
)
app.register_blueprint(google_bp, url_prefix="/google_login")

    from datetime import datetime, timedelta
    @app.context_processor
    def inject_utilities():
        return dict(Config=Config, timedelta=timedelta, current_year=datetime.utcnow().year)

    # Import scheduled jobs and add them to the scheduler
    from app.scheduled_jobs import check_trial_expiry_and_notify, check_subscription_expiry_and_notify
    scheduler.add_job(id='trial_expiry_job', func=check_trial_expiry_and_notify, trigger='interval', seconds=86400)
    scheduler.add_job(id='subscription_expiry_job', func=check_subscription_expiry_and_notify, trigger='interval', seconds=86400)

    return app
