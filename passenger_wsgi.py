"""cPanel Python App / Phusion Passenger entry point.

Set the cPanel Application root to the directory containing this file,
manage.py, and the alvis/ package. Set the startup file to passenger_wsgi.py
and the entry point to application.
"""
import os
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alvis.settings")
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
