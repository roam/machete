# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)


class RequestContext(object):

    def __init__(self, request, pks, mode, status=200):
        self.request = request
        self.pks = pks
        self.nr_pks = len(pks)
        self.pk = None if self.nr_pks != 1 else self.pks[0]
        self.mode = mode
        self.status = status


class RequestWithResourceContext(RequestContext):

    def __init__(self, request, pks, mode, resource, resources, many, status=200):
        super(RequestWithResourceContext, self).__init__(request, pks, mode, status=status)
        self.resource = resource
        self.resources = resources
        self.many = many


def pluck_ids(data, name=None):
    if name:
        items = data[name]
    else:
        items = data
    if not isinstance(items, list):
        items = [items]
    return ['%s' % i['id'] for i in items]
