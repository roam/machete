# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)


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
