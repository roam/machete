# -*- coding: utf-8 -*-
import sys
from django import VERSION
from django.conf import settings
from django.core.management import execute_from_command_line

if not settings.configured:
    test_runners_args = {}
    if VERSION < (1, 6):
        test_runners_args = {
            'TEST_RUNNER': 'discover_runner.DiscoverRunner',
        }
    settings.configure(
        INSTALLED_APPS = (
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'machete',
            'tests',
        ),
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3'
            }
        },
        SECRET_KEY = 'ohno',
        ROOT_URLCONF = None
    )


if __name__ == '__main__':
    argv = sys.argv[:1] + ['test'] + sys.argv[1:]
    execute_from_command_line(argv)
