from .base import *

import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)

DEBUG = False

SECRET_KEY = os.getenv('SECRET_KEY')

# Email SMTP settings
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = os.getenv('EMAIL_PORT')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS')
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL')
EMAIL_SSL_KEYFILE = os.getenv('EMAIL_SSL_KEYFILE')
EMAIL_SSL_CERTFILE = os.getenv('EMAIL_SSL_CERTFILE')

ALLOWED_HOSTS = ['.example.com']

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

try:
    from .local import *
except ImportError:
    pass
