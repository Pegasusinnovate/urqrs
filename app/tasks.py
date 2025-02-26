import os
# Signal that this app instance is being created for a Celery worker.
os.environ['CELERY_WORKER'] = '1'

from celery import Celery
from flask_mail import Message
from app import create_app, mail
import logging

app = create_app()
celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@celery.task
def send_async_email(msg_data):
    with app.app_context():
        try:
            msg = Message(**msg_data)
            mail.send(msg)
        except Exception as e:
            logging.error("Failed to send async email: %s", e)