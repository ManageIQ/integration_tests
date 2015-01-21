"""
Django settings for sprout project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""
from __future__ import absolute_import
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from datetime import timedelta
import os

from utils.conf import cfme_data, credentials

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = credentials["sprout"]["key"]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_DEBUG", "false") == "true"

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1"
]


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'appliances',
    'django_object_actions',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.messages.context_processors.messages',
    'django.contrib.auth.context_processors.auth',
    "django.core.context_processors.request",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    'appliances.context_processors.hubber_url',
)

MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

ROOT_URLCONF = 'sprout.urls'

WSGI_APPLICATION = 'sprout.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)

# STATIC_ROOT = os.path.join(BASE_DIR, '_static')

# CELERY SETTINGS
REDIS_PORT = os.environ.get("REDIS_PORT", 6379)
BROKER_URL = 'redis://127.0.0.1:{}/{}'.format(REDIS_PORT, os.environ.get("REDIS_DB_ID", 0))
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:{}/{}'.format(
    REDIS_PORT, os.environ.get("REDIS_RESULT_DB_ID", 1))
# CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'pickle'
CELERY_RESULT_SERIALIZER = 'pickle'
CELERY_TIMEZONE = "UTC"
CELERY_DISABLE_RATE_LIMITS = True
CELERY_TIMEZONE = 'UTC'
# CELERY_ACKS_LATE = True
# CELERYD_PREFETCH_MULTIPLIER = 1

TRACKERBOT_URL = cfme_data["sprout"]["trackerbot_url"]
# TODO: To be able to use RHEV-M (and other EMSs), the mgmt_system for it must have
# TODO: .mark_as_template implemented. Then it can be used.
TEMPLATE_FORMAT = "sprout_template_{group}_{date}_{rnd}"
APPLIANCE_FORMAT = "sprout_appliance_{group}_{date}_{rnd}"

# General redis settings
GENERAL_REDIS = dict(host='127.0.0.1', port=REDIS_PORT, db=int(os.environ.get("REDIS_GENERAL", 2)))


ATOMIC_REQUESTS = False  # Turn off after moving to postgre

HUBBER_URL = None

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:{}'.format(os.environ.get("MEMCACHED_PORT", 23156)),
    }
}

BROKEN_APPLIANCE_GRACE_TIME = dict(
    hours=1,
)

# Celery beat
CELERYBEAT_SCHEDULE = {
    'retrieve-appliances-power-states': {
        'task': 'appliances.tasks.retrieve_appliances_power_states',
        'schedule': timedelta(minutes=2),
    },

    'free-appliance-shepherd': {
        'task': 'appliances.tasks.free_appliance_shepherd',
        'schedule': timedelta(minutes=5),
    },

    'kill-unused-appliances': {
        'task': 'appliances.tasks.kill_unused_appliances',
        'schedule': timedelta(minutes=1),
    },

    'delete-nonexistent-appliances': {
        'task': 'appliances.tasks.delete_nonexistent_appliances',
        'schedule': timedelta(minutes=10),
    },

    'poke-providers': {
        'task': 'appliances.tasks.poke_providers',
        'schedule': timedelta(minutes=10),
    },

    'poke-trackerbot': {
        'task': 'appliances.tasks.poke_trackerbot',
        'schedule': timedelta(minutes=10),
    },

    'retrieve-template-existence': {
        'task': 'appliances.tasks.retrieve_template_existence',
        'schedule': timedelta(minutes=15),
    },

    'process-delayed-provision-tasks': {
        'task': 'appliances.tasks.process_delayed_provision_tasks',
        'schedule': timedelta(seconds=20),
    },
}

try:
    from sprout.local_settings import *  # NOQA
except ImportError:
    pass
