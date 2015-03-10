import os

def pytest_configure():
    from django.conf import settings

    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={'default':
            {'ENGINE': 'django.db.backends.sqlite3',
             'NAME': ':memory:',
             'TEST_NAME': os.path.join(os.path.dirname(__file__), 'test.db')}
        },
        SITE_ID=1,
        SECRET_KEY='not very secret in tests',
        USE_I18N=True,
        USE_L10N=True,
        STATIC_URL='/static/',
        ROOT_URLCONF='tests.urls',
        TEMPLATE_LOADERS=(
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ),
        MIDDLEWARE_CLASSES=(
            'django.middleware.common.CommonMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ),
        INSTALLED_APPS=(
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'rest_framework',
            'tests',
        ),
        REST_FRAMEWORK={
          'DEFAULT_RENDERER_CLASSES': (
            'ember_drf.renderers.ActiveModelJSONRenderer',
            'rest_framework.renderers.BrowsableAPIRenderer',
          ),
          'DEFAULT_PARSER_CLASSES': (
            'ember_drf.parsers.ActiveModelJSONParser',
            'rest_framework.parsers.FormParser',
            'rest_framework.parsers.MultiPartParser',
          ),
          'DEFAULT_FILTER_BACKENDS': (
            'rest_framework.filters.DjangoFilterBackend',
            'ember_drf.filters.CoallesceIDsFilterBackend'
          ),
          'EXCEPTION_HANDLER': 'ember_drf.views.exception_handler',
          'TEST_REQUEST_DEFAULT_FORMAT': 'json',
        }
    )

    try:
        import django
        django.setup()
    except AttributeError:
        pass
