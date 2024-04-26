import os

SECRET_KEY = 'fake-key'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GOOGLE_RECAPTCHA_SECRET_KEY = 'fake-recaptcha-secret'
GOOGLE_RECAPTCHA_SITE_KEY = 'fake-recaptcha-key'
GOOGLE_TAG_ID = 'GTM-P4BQ99S'

GOOGLE_MAPS_KEY = 'fake-gmaps-key'
GRID_DISPLAY_COUNT = 3

MEDIA_ROOT = os.path.join(BASE_DIR, 'media2', 'media')

CSS_VERSION = 1


KF_DJANGOCMS_NAVIGATION = False
KF_DJANGOCMS_SUPPORT = False
KF_DJANGOCMS_ROOT = 'iowa'
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.contenttypes',
    'archive.apps.ArchiveConfig',
    'django.contrib.gis',
    'django.contrib.sites',
    'tests',
    'gtm',
]
ROOT_URLCONF = 'tests.urls'
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite',
        'NAME': ":memory:",
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'archive.context_processors.kronofoto_context',
            ],
        },
    },
]
SITE_ID = 1
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]
LOCAL_CONTEXTS = 'https://anth-ja77-lc-dev-42d5.uc.r.appspot.com/api/v1/'
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    },
}

AUTHENTICATION_BACKENDS = ['archive.auth.backends.ArchiveBackend']
KF_URL_SCHEME = ""
GOOGLE_RECAPTCHA3_SITE_KEY = 'google_test_key'
GOOGLE_RECAPTCHA3_SECRET_KEY = 'google_secret_key'
USE_TZ = True
IMAGE_CACHE_URL_PREFIX = ''
