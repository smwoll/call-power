import os

from werkzeug.contrib.fixers import ProxyFix

from app import create_app
from extensions import assets


assets._named_bundles = {}
application = create_app()
# requires application context
assets.auto_build = False

if os.environ.get('SENTRY_DSN'):
    from raven.contrib.flask import Sentry
    sentry = Sentry()
    sentry.init_app(application)

application.wsgi_app = ProxyFix(application.wsgi_app)