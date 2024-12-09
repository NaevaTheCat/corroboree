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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'OPTIONS': {
            'read_default_file': os.path.join(BASE_DIR, 'corroboree/settings/my.cnf'),
        },
    }
}


LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
                'superverbose': {
                        'format': '%(levelname)s %(asctime)s %(module)s:%(lineno)d %(process)d %(thread)d %(message)s'
                        },
                'verbose': {
                        'format': '%(levelname)s %(asctime)s %(module)s:%(lineno)d %(message)s'
                        },
                'simple': {
                        'format': '%(levelname)s %(message)s'
                        },
        },
        'handlers': {
                'console': {
                        'class': 'logging.StreamHandler',
                        'formatter': 'verbose',
                        },
                },
        'root': {
                'handlers': ['console'],
                'level': 'INFO',
                'formatter': 'verbose',
                },
        'loggers': {
                'django.utils.autoreload': {
                        'handlers': [],
                        'level': 'ERROR',
                        },

                'django': {
                        'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
                        'handlers': ['console'],
                        'propagate': True,
                        },
                }
        }

try:
    from .local import *
except ImportError:
    pass
