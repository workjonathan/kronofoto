import os
from decouple import config, Csv
from datetime import datetime

CSS_VERSION = (int(datetime.now().timestamp()) >> 3) & 127
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_ID = 1
DEBUG = False

SECRET_KEY = config("SECRET_KEY")
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
USE_X_FORWARDED_HOST = True

GOOGLE_RECAPTCHA_SECRET_KEY = config('GOOGLE_RECAPTCHA_SECRET_KEY')
GOOGLE_RECAPTCHA_SITE_KEY = config('GOOGLE_RECAPTCHA_SITE_KEY')
GOOGLE_RECAPTCHA3_SITE_KEY = config('GOOGLE_RECAPTCHA3_SITE_KEY')
GOOGLE_RECAPTCHA3_SECRET_KEY = config('GOOGLE_RECAPTCHA3_SECRET_KEY')
GOOGLE_TAG_ID = config('GOOGLE_TAG_ID')

try:
    EMAIL_HOST = config("EMAIL_HOST")
except:
    pass
try:
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')
except:
    pass

try:
    GOOGLE_MAPS_KEY = config('GOOGLE_MAPS_KEY')
except:
    pass

DATABASES = {
    'default': {
        'ENGINE': config("DB_ENGINE"),
        'NAME': config("DB_NAME"),
        'USER': config("DB_USER"),
        'PASSWORD': config("DB_PASSWORD"),
        'HOST': config("DB_HOST")
    }
}

INSTALLED_APPS = [
    'robots',
    'django.contrib.admin',
    'django.contrib.sitemaps',
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
]

MIDDLEWARE = [
    'fortepan_us.kronofoto.middleware.OverrideVaryMiddleware',
    'fortepan_us.kronofoto.middleware.AnonymizerProtectionMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'fortepan_us.kronofoto.middleware.ActorAuthenticationMiddleware',
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
]

ROOT_URLCONF = 'fortepan_us.settings.urls'

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

CMS_TEMPLATES = [
    ('archive/cms-base.html', 'Default'),
]

LANGUAGE_CODE = 'en-us'

LANGUAGES = [
    ('en-us', 'English'),
]

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

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

WSGI_APPLICATION = 'fortepan_us.settings.wsgi.application'

KF_DJANGOCMS_NAVIGATION = True
KF_DJANGOCMS_SUPPORT = True
KF_DJANGOCMS_ROOT = config("KF_DJANGOCMS_ROOT", default='us')
X_FRAME_OPTIONS = 'SAMEORIGIN'

STATIC_URL = config('STATIC_URL')
MEDIA_ROOT = config('MEDIA_ROOT')
MEDIA_URL = config('MEDIA_URL')
STATIC_ROOT = config('STATIC_ROOT')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'kfcache',
        'OPTIONS': {"MAX_ENTRIES": 50000},
    }
}

GRID_DISPLAY_COUNT = 48
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
LOGIN_REDIRECT_URL = '/'
ENCRYPTION_KEY = config("ENCRYPTION_KEY", cast=lambda s: s.encode("utf-8"))
try:
    os.environ['http_proxy'] = config("HTTP_PROXY")
except:
    pass
try:
    os.environ['https_proxy'] = config("HTTPS_PROXY")
except:
    pass
LOCAL_CONTEXTS = 'https://localcontextshub.org/api/v1/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
		'null': {
			'level': 'DEBUG',
			'class': 'logging.NullHandler',
		},
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
		'django.security.DisallowedHost': {
			'handlers': ['null'],
			'propagate': False,
		},
	},
}

AUTHENTICATION_BACKENDS = ['fortepan_us.kronofoto.auth.backends.ArchiveBackend']

ADMINS = [
    (name, email)
    for (name, email) in zip(
        config("ADMIN_NAMES", cast=Csv(), default=""),
        config("ADMIN_EMAILS", cast=Csv(), default=""),
    )
]

KRONOFOTO_SEARCH_LIMIT = 60
IMAGE_CACHE_URL_PREFIX = config("IMAGE_CACHE_URL_PREFIX")
