import os
import dj_database_url
from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent.parent
env=os.environ.get
DEBUG=env('DEBUG','False')=='True'
SECRET_KEY=env('SECRET_KEY') or ('dev-only-insecure-key' if DEBUG else None)
if not SECRET_KEY: raise RuntimeError('SECRET_KEY is required when DEBUG is False')
_host=env('RENDER_EXTERNAL_HOSTNAME')
ALLOWED_HOSTS=[h for h in env('ALLOWED_HOSTS','localhost,127.0.0.1').split(',') if h]+([_host] if _host else [])
CSRF_TRUSTED_ORIGINS=[o for o in env('CSRF_TRUSTED_ORIGINS','').split(',') if o]+([f'https://{_host}'] if _host else [])
INSTALLED_APPS=['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','apps.accounts','apps.core','apps.members','apps.executives','apps.projects','apps.events','apps.comms','apps.impact']
MIDDLEWARE=['apps.core.middleware.HealthCheckMiddleware','django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='config.urls'
WSGI_APPLICATION='config.wsgi.application'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages','apps.comms.context.unread']}}]
if not env('DATABASE_URL'): raise RuntimeError('DATABASE_URL is required (PostgreSQL in production; sqlite:/// only for local tests)')
DATABASES={'default':dj_database_url.config(conn_max_age=600,conn_health_checks=True,ssl_require=env('DB_SSL_REQUIRE','False')=='True')}
AUTH_USER_MODEL='accounts.User'
AUTHENTICATION_BACKENDS=['apps.accounts.backends.RoleBackend']
AUTH_PASSWORD_VALIDATORS=[{'NAME':f'django.contrib.auth.password_validation.{n}'} for n in ('UserAttributeSimilarityValidator','MinimumLengthValidator','CommonPasswordValidator','NumericPasswordValidator')]
LOGIN_URL='login'; LOGIN_REDIRECT_URL='dashboard'; LOGOUT_REDIRECT_URL='home'
REQUIRE_EMAIL_VERIFICATION=env('REQUIRE_EMAIL_VERIFICATION','False')=='True'
EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'  # replace when an email provider is chosen
LANGUAGE_CODE='en-gb'; TIME_ZONE='Africa/Lagos'; USE_I18N=True; USE_TZ=True
STATIC_URL='/static/'; STATIC_ROOT=BASE_DIR/'staticfiles'; STATICFILES_DIRS=[BASE_DIR/'static']
MEDIA_URL='/media/'; MEDIA_ROOT=BASE_DIR/'media'  # ephemeral on Render: see README before enabling uploads
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
DATA_UPLOAD_MAX_MEMORY_SIZE=5*1024*1024; FILE_UPLOAD_MAX_MEMORY_SIZE=5*1024*1024
if not DEBUG:
    STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'whitenoise.storage.CompressedStaticFilesStorage'}}
    SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https'); SECURE_SSL_REDIRECT=True; SECURE_REDIRECT_EXEMPT=[r'^health/$']
    SESSION_COOKIE_SECURE=CSRF_COOKIE_SECURE=True; SECURE_HSTS_SECONDS=31536000; SECURE_HSTS_INCLUDE_SUBDOMAINS=True
    SECURE_CONTENT_TYPE_NOSNIFF=True; X_FRAME_OPTIONS='DENY'
