import os

from .base import *  # noqa: F401,F403

DEBUG = False

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
