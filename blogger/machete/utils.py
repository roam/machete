# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from django.core.exceptions import ImproperlyConfigured


class RequestPayloadDescriptor(object):

    def __init__(self, name, resources, resource=None):
        self.name = name
        self.resources = resources
        self.resource = resource
        self.many = resource is None


class RequestRelationshipDescriptor(object):

    def __init__(self, name, pks=None, many=False):
        if not many and self.pks:
            raise ImproperlyConfigured('You cannot pass ids for a to-one '
                                       'relationship')
        self.name = name
        self.pks = pks or []
        self.pk = None if len(self.pks) != 1 else self.pks[0]


class RequestResourceDescriptor(object):

    def __init__(self, name, pks=None, relationship_descriptor=None):
        self.name = name
        self.pks = pks or []
        self.nr_pks = len(self.pks)
        self.pk = None if self.nr_pks != 1 else self.pks[0]
        self.relationship_descriptor = relationship_descriptor


class RequestContext(object):

    def __init__(self, request, resource_descriptor, status=200):
        self.request = request
        self.resource_descriptor = resource_descriptor
        self.status = status
        self.mode = None

    def update_mode(self, request_method):
        self.mode = self.determine_mode(request_method)

    def determine_mode(self, request_method):
        descriptor = self.resource_descriptor
        if request_method == 'GET':
            if descriptor.pk:
                return 'get:single'
            if descriptor.pks:
                return 'get:multiple'
            return 'get:all'
        if request_method == 'DELETE':
            if descriptor.pk:
                return 'delete:single'
            if descriptor.pks:
                return 'delete:multiple'
            return 'delete:all'
        return None

    @classmethod
    def create_resource_descriptor(cls, name, pks=None, relationship_descriptor=None):
        return RequestResourceDescriptor(name, pks, relationship_descriptor)

    @classmethod
    def create_relationship_descriptor(cls, name, pks=None, many=False):
        return RequestRelationshipDescriptor(name, pks, many)

    @property
    def pk(self):
        return self.resource_descriptor.pk

    @property
    def pks(self):
        return self.resource_descriptor.pks

    @property
    def requested_single_resource(self):
        return self.pk is not None


class RequestWithResourceContext(RequestContext):

    def __init__(self, request, resource_descriptor, payload, status=200):
        super(RequestWithResourceContext, self).__init__(request, resource_descriptor, status=status)
        self.payload = payload

    def determine_mode(self, request_method):
        regular = super(RequestWithResourceContext, self).determine_mode(request_method)
        if regular is not None:
            return regular
        payload = self.payload
        if request_method == 'POST':
            if payload.many:
                return 'create:multiple'
            return 'create:single'
        if request_method == 'PUT':
            if payload.many:
                return 'update:multiple'
            return 'update:single'
        return None


def pluck_ids(data, name=None):
    if name:
        items = data[name]
    else:
        items = data
    if not isinstance(items, list):
        items = [items]
    return ['%s' % i['id'] for i in items]
