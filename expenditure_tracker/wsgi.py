"""
WSGI config for expenditure_tracker project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expenditure_tracker.settings')

application = get_wsgi_application()

# When using pythonanywhere
# import os
# import sys
#
# path = '/home/cwa/CWA'
# if path not in sys.path:
#     sys.path.append(path)
#
# os.environ['DJANGO_SETTINGS_MODULE'] = 'expenditure_tracker.settings'
#
# from django.core.wsgi import get_wsgi_application
# application = get_wsgi_application()
