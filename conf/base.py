# -*- coding: utf-8 -*-

from .defaults import *
from datetime import timedelta
import environ

env = environ.Env(DEBUG=(bool, False),) # set default values and casting
ZAPPA=os.environ.get('is_zappa', '') == 'true'
DEBUG=os.environ.get('DEBUG', '') != 'false' or not ZAPPA


INSTALLED_APPS = [
    'django.contrib.auth',
    'jet.dashboard',
    'jet',
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',

    'django_s3_storage',
    'rest_framework',
    'rest_registration',
    'auditlog',

    'django_filters',
    'django_extensions',

    'apps.users',
    'apps.invoices'

]

REST_REGISTRATION = {
    'REGISTER_VERIFICATION_ENABLED': False,
    'REGISTER_VERIFICATION_URL': 'https://paywei.co/verify-user/',
    'RESET_PASSWORD_VERIFICATION_URL': 'https://paywei.co/reset-password/',
    'REGISTER_EMAIL_VERIFICATION_URL': 'https://paywei.co/verify-email/',
    'VERIFICATION_FROM_EMAIL': 'noreply@paywei.co',
    'PROFILE_SERIALIZER_CLASS': 'apps.users.serializers.UserProfileSerializer',
    'USER_EDITABLE_FIELDS': ['email', 'username', 'first_name', 'last_name', 'default_pricing_currency', 'default_address']
}

AUTH_USER_MODEL = 'users.CustomUser'

DATABASES = {
    'default': env.db('DATABASE_URL', default='psql://paywei:paywei@psql/paywei'),
}

LOGGING['loggers']['scanner'] = {
    'handlers': ['console'],
    'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG')
}

LOGGING['loggers']['subscriptions'] = {
    'handlers': ['console'],
    'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG')
}

TEMPLATES = [
    {
        # See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        'DIRS': [
            str(SITE_ROOT + '/templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
            'debug': DEBUG,
            # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
            # https://docs.djangoproject.com/en/dev/ref/templates/api/#loader-types
            # 'loaders': [
            #     'django.template.loaders.filesystem.Loader',
            #     'django.template.loaders.app_directories.Loader',
            # ],
            # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                # Your stuff: custom template context processors go here
            ],
        },
    },
]

ALLOWED_HOSTS = ['paywei.co', '127.0.0.1', 'localhost', '*']

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'apps.users.authentication.APIKeyAuthentication',)
}

AWS_S3_BUCKET_NAME_STATIC = 'zappa-paywei-static'
AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_S3_BUCKET_NAME_STATIC

if ZAPPA:
    BASE_URL="https://api.paywei.co"
else:
    BASE_URL="http://localhost:9000"

if ZAPPA:
    STATICFILES_STORAGE = "django_s3_storage.storage.StaticS3Storage"
    AWS_REGION = "us-east-2"

    STATIC_URL = "https://%s/"%AWS_S3_CUSTOM_DOMAIN

    EMAIL_BACKEND = 'django_ses.SESBackend'

    # Additionally, if you are not using the default AWS region of us-east-1,
    # you need to specify a region, like so:
    AWS_SES_REGION_NAME = 'us-east-1'
    AWS_SES_REGION_ENDPOINT = 'email.us-east-1.amazonaws.com'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

APPEND_SLASH=True


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}

CMC_API_KEY = 'a79b1aa0-36c0-45d1-980f-b951eb4382b1'

METRIC_ACCESS_KEY_ID = os.environ.get('METRIC_ACCESS_KEY_ID', '')
METRIC_SECRET_ACCESS_KEY = os.environ.get('METRIC_SECRET_ACCESS_KEY', '')
