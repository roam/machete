# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from django.core.urlresolvers import reverse


def to_absolute_url(relative_url, request=None):
    if request:
        return request.build_absolute_uri(relative_url)
    # TODO Use some setting
    return relative_url


def get_resource_detail_url(name, pks, **kwargs):
    pks = ','.join('%s' % i for i in pks)
    kwargs['pks'] = pks
    return reverse(create_resource_view_name(name), kwargs=kwargs)


def create_resource_view_name(resource_name):
    return 'api_%s_detail' % resource_name


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
