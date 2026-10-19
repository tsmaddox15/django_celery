"""Print the settings module and the exact ODBC connection string Django uses.

Run inside the container that fails, e.g. `docker compose exec beat python dbcheck.py`.
Delete this file once the connection works.
"""
import os
import re

import django
import pyodbc

print('DJANGO_SETTINGS_MODULE =', os.environ.get('DJANGO_SETTINGS_MODULE'))
django.setup()

from django.conf import settings  # noqa: E402
from django.db import connection  # noqa: E402

print('settings loaded from   =', settings.SETTINGS_MODULE)
db = settings.DATABASES['default']
print('USER =', repr(db.get('USER')), '| PASSWORD set =', bool(db.get('PASSWORD')))
print('OPTIONS =', db.get('OPTIONS'))

real_connect = pyodbc.connect


def spy(connstr, *args, **kwargs):
    # Never print the password itself.
    print('ODBC connection string =', re.sub(r'(?i)(PWD=)[^;]*', r'\1***', connstr))
    return real_connect(connstr, *args, **kwargs)


pyodbc.connect = spy
connection.ensure_connection()
print('CONNECTED OK')
