"""WSGI config for BlueRock Group investments.

Used by cPanel Passenger and other WSGI servers.
"""
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alvis.settings")
application = get_wsgi_application()
