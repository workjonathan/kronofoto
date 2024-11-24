import os
from datetime import datetime
from decouple import config, Csv # type: ignore

CSS_VERSION = (int(datetime.now().timestamp()) >> 3) & 127

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SITE_ID = 1

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'fortepan_us.kronofoto',
    'django.contrib.gis',
    'django.contrib.sites',
    'gtm',
    'djgeojson',
    'mptt',
    'cms',
    'menus',
    'treebeard',
    'sekizai',
    'filer',
    'djangocms_picture',
    'djangocms_file',
    'djangocms_text_ckeditor',
    'djangocms_link',
    'easy_thumbnails',
    'debug_toolbar',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'fortepan_us.kronofoto.middleware.ActorAuthenticationMiddleware',
    'fortepan_us.kronofoto.middleware.OverrideVaryMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'fortepan_us.kronofoto.middleware.CorsMiddleware',
	'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.toolbar.ToolbarMiddleware',
    'cms.middleware.language.LanguageCookieMiddleware',
]

ROOT_URLCONF = 'fortepan_us.settings.dev_urls'

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
                'fortepan_us.kronofoto.context_processors.kronofoto_context',
                'sekizai.context_processors.sekizai',
            ],
        },
    },
]

WSGI_APPLICATION = 'fortepan_us.settings.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite',
        'NAME': os.path.join(BASE_DIR, 'db2.sqlite3'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

LANGUAGES = [
    ('en-us', 'English'),
]

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = '/static/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

#STATICFILES_DIRS = [
#    os.path.join(BASE_DIR, 'static'),
#]

LOGIN_REDIRECT_URL = '/'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'kfcache',
    }
}

GRID_DISPLAY_COUNT = 48
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

IMAGE_CACHE_URL_PREFIX = ""
KRONOFOTO_SEARCH_LIMIT = 60

DEBUG = True

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv(), default="localhost, 127.0.0.1")

ENCRYPTION_KEY = config("ENCRYPTION_KEY", cast=bytes, default=b"secret-encryption-key")

SECRET_KEY = config("SECRET_KEY")

GOOGLE_RECAPTCHA_SECRET_KEY = config("GOOGLE_RECAPTCHA_SECRET_KEY", default="fake-secret")
GOOGLE_RECAPTCHA_SITE_KEY = config("GOOGLE_RECAPTCHA_SITE_KEY", default="fake-key")
GOOGLE_RECAPTCHA3_SECRET_KEY = config("GOOGLE_RECAPTCHA3_SECRET_KEY", default="fake-secret")
GOOGLE_RECAPTCHA3_SITE_KEY = config("GOOGLE_RECAPTCHA_SITE_KEY", default="fake-key")

GOOGLE_TAG_ID = config("GOOGLE_TAG_ID", default="fake-gtm")

INTERNAL_IPS = [
    '127.0.0.1',
]

LOCAL_CONTEXTS = 'https://anth-ja77-lc-dev-42d5.uc.r.appspot.com/api/v1/'
DEBUG_TOOLBAR_CONFIG = {
    "ROOT_TAG_EXTRA_ATTRS": "hx-preserve",
    "RESULTS_CACHE_SIZE": 200,
}

CMS_TEMPLATES = [
    ('archive/cms-base.html', 'Default'),
]

KF_DJANGOCMS_NAVIGATION = True
KF_DJANGOCMS_SUPPORT = True
KF_DJANGOCMS_ROOT = 'iowa'
KF_URL_SCHEME = "http:"

AUTHENTICATION_BACKENDS = ['fortepan_us.kronofoto.auth.backends.ArchiveBackend']
APPEND_SLASH = False
AUTH_PASSWORD_VALIDATORS = []
