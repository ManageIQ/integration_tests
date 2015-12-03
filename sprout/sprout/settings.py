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

from utils.conf import credentials

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = credentials["sprout"]["key"]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_DEBUG", "false") == "true"

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

MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

ROOT_URLCONF = 'sprout.urls'

WSGI_APPLICATION = 'sprout.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.messages.context_processors.messages',
                'django.contrib.auth.context_processors.auth',
                "django.template.context_processors.request",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                'appliances.context_processors.hubber_url',
                'appliances.context_processors.sprout_needs_update',
            ],
            'debug': True,
            'builtins': [
                'appliances.templatetags.appliances_extras',
            ],
        },
    },
]


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
CELERYD_MAX_TASKS_PER_CHILD = int(os.environ.get("MAX_TASKS_PER_WORKER", 50))
# CELERY_ACKS_LATE = True
# CELERYD_PREFETCH_MULTIPLIER = 1

# TODO: To be able to use RHEV-M (and other EMSs), the mgmt_system for it must have
# TODO: .mark_as_template implemented. Then it can be used.
TEMPLATE_FORMAT = "s_tpl_{group}_{date}_{rnd}"
APPLIANCE_FORMAT = "s_appl_{group}_{date}_{rnd}"

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

ORPHANED_APPLIANCE_GRACE_TIME = dict(
    minutes=45,
)

# Celery beat
CELERYBEAT_SCHEDULE = {
    'check-templates': {
        'task': 'appliances.tasks.check_templates',
        'schedule': timedelta(minutes=17),
    },

    'refresh-appliances': {
        'task': 'appliances.tasks.refresh_appliances',
        'schedule': timedelta(minutes=7),
    },

    'free-appliance-shepherd': {
        'task': 'appliances.tasks.free_appliance_shepherd',
        'schedule': timedelta(seconds=30),
    },

    'kill-unused-appliances': {
        'task': 'appliances.tasks.kill_unused_appliances',
        'schedule': timedelta(minutes=1),
    },

    'delete-nonexistent-appliances': {
        'task': 'appliances.tasks.delete_nonexistent_appliances',
        'schedule': timedelta(minutes=10),
    },

    'poke-trackerbot': {
        'task': 'appliances.tasks.poke_trackerbot',
        'schedule': timedelta(minutes=10),
    },

    'process-delayed-provision-tasks': {
        'task': 'appliances.tasks.process_delayed_provision_tasks',
        'schedule': timedelta(seconds=20),
    },

    'check-update': {
        'task': 'appliances.tasks.check_update',
        'schedule': timedelta(minutes=15),
    },

    'scavenge-managed-providers': {
        'task': 'appliances.tasks.scavenge_managed_providers',
        'schedule': timedelta(minutes=30),
    },

    'mailer-version-mismatch': {
        'task': 'appliances.tasks.mailer_version_mismatch',
        'schedule': timedelta(minutes=60),
    },

    'obsolete-template-deleter': {
        'task': 'appliances.tasks.obsolete_template_deleter',
        'schedule': timedelta(days=1),
    },
}

try:
    from sprout.local_settings import *  # NOQA
except ImportError:
    pass
