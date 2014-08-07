# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from datetime import datetime

from django import forms
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

import django_filters


class QuerySetMethodFilter(django_filters.Filter):

    def __init__(self, *args, **kwargs):
        self.method = kwargs.pop('method')
        self.method_args = kwargs.pop('method_args', [])
        self.method_kwargs = kwargs.pop('method_kwargs', {})
        super(QuerySetMethodFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        args = [value] + self.method_args
        kwargs = self.method_kwargs
        return getattr(qs, self.method)(*args, **kwargs)


class SearchFilter(QuerySetMethodFilter):

    def __init__(self, *args, **kwargs):
        kwargs['method'] = 'search'
        super(SearchFilter, self).__init__(*args, **kwargs)


class UtcDateTimeField(forms.DateTimeField):

    def to_python(self, value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            if value.endswith('Z'):
                value = value[:-1]
            o = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
            o = timezone.make_aware(o, timezone.utc)
            if not getattr(settings, 'USE_TZ', False):
                o = timezone.make_naive(o, timezone.get_default_timezone())
            return o
        except ValueError:
            raise ValidationError(self.error_messages['invalid'])


class UtcDateTimeFilter(django_filters.Filter):
    field_class = UtcDateTimeField
