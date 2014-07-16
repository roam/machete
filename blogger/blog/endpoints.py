# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

import json

from marshmallow import class_registry
from django.views.generic import View
from django.http import HttpResponse

from .models import Post
from .serializers import serialize


class JsonApiObject(object):
    pass


class ResourceObject(JsonApiObject):

    def __init__(self, name, resource):
        self.name = name
        self.resource = resource


class ResourceId(JsonApiObject):

    def __init__(self, name, pk):
        self.name = name
        self.pk = pk


class ResourceCollectionArray(JsonApiObject):

    def __init__(self, name, resource_objects):
        self.name = name
        self.resource_objects = resource_objects


class ResourceCollectionIds(JsonApiObject):

    def __init__(self, name, resource_ids):
        self.name = name
        self.resource_ids = resource_ids


class ResourceCollectionObject(JsonApiObject):

    def __init__(self, name, href, pks, type_name):
        self.name = name
        self.href = href
        self.pks = pks
        self.type_name = type_name


class Endpoint(View):
    content_type = 'application/json'

    def dispatch(self, request, *args, **kwargs):
        result = super(Endpoint, self).dispatch(request, *args, **kwargs)
        if isinstance(result, JsonApiObject):
            data = self.to_json(result, indent=self.get_indent())
            return HttpResponse(data, content_type=self.get_content_type())
        return result

    def __get(self, request, *args, **kwargs):
        ids = kwargs.get('ids', None)
        if ids:
            ids = ids.split(',')
            if len(ids) > 1:
                return self.get_multiple_resources(ids)
            return self.get_resource(ids[0])
        return self.get_multiple_resources()

    def __post(self, request, *args, **kwargs):
        body = json.loads(request.body)
        name = self.get_name()
        resources = body.get(name)
        if not isinstance(resources, list):
            resources = [resources]
        created = []
        failed = []
        for resource in resources:
            item, errors = self.create(resource)
            if errors:
                failed.append((resource, errors))
            else:
                created.append(item)
        if failed:
            return HttpResponse('error')
        return None

    def create(self, resource):
        pass

    def get_resource(self, id):
        pass

    def get_multiple_resources(self, ids=None):
        pass

    def get_content_type(self):
        return self.content_type

    def get_serializer_class(self):
        return class_registry.get_class(self.get_name())

    def get_name(self):
        return self.name

    def get_indent(self):
        if hasattr(self, 'indent'):
            return self.indent
        return 2

    def to_json(self, data, **kwargs):
        return json.dumps(data, **kwargs)

    def compose_compound(self):
        return getattr(self, 'compound', False)

    def build_jsonapi_data(self, resource=None, resources=None):
        to_serialize = resource
        many = False
        if resources:
            to_serialize = resources
            many = True
        serializer = self.get_serializer_class()
        compound = self.compose_compound()
        return serialize(self.get_name(), to_serialize, many=many, serializer=serializer, compound=compound)


class ModelEndpoint(Endpoint):

    def get_queryset(self):
        if hasattr(self, 'queryset'):
            return self.queryset
        return self.model.objects.all()

    def create(self, resource):
        form_kwargs = {'data': resource}
        form = self.get_form(**form_kwargs)
        if form.is_valid():
            return ResourceObject(form.save()), None
        return None, form.errors

    def get_form(self, **kwargs):
        if not kwargs:
            kwargs = {}
        kwargs = dict(kwargs + self.get_form_kwargs())
        return self.get_form_class(**kwargs)

    def get_form_kwargs(self):
        return {}

    def get_pk_field(self):
        if hasattr(self, 'pk_field'):
            return self.pk_field
        return 'pk'

    def get_resource(self, id):
        filter = {self.get_pk_field(): id}
        resource = self.get_queryset().get(**filter)
        return self.build_jsonapi_data(resource=resource)

    def get_multiple_resources(self, ids=None):
        qs = self.get_queryset()
        if ids:
            filter = {'%s__in' % self.get_pk_field(): ids}
            qs = qs.filter(**filter)
        return self.build_jsonapi_data(resources=qs)


class PostEndpoint(ModelEndpoint):
    name = 'posts'
    model = Post
    compound = True
