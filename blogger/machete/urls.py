# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from django.core.urlresolvers import reverse


def to_absolute_url(relative_url, request=None):
    if request:
        return request.build_absolute_uri(relative_url)
    # TODO Use some setting
    return relative_url


def get_resource_detail_url(name, ids):
    return '/resource/%s/%s' % (name, ','.join('%s' % i for i in ids))


def get_resource_url_template(viewname, template, urlconf=None, kwargs=None, prefix=None, current_app=None, ids_group_name=None):
    if not ids_group_name:
        ids_group_name = 'pks'
    if not kwargs:
        kwargs = {}
    placeholder = '123456789'
    while placeholder in kwargs.values():
        placeholder += placeholder
    kwargs[ids_group_name] = placeholder
    result = reverse(viewname, urlconf=urlconf, kwargs=kwargs, prefix=prefix, current_app=None)
    return result.replace(placeholder, template)
