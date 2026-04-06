import os
from .base import *

DEBUG = True
SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-me-in-development')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
