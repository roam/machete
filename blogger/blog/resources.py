# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

import json

from marshmallow import class_registry

from .models import Post
from .serializers import serialize


class Resource(object):

    def get_queryset(self):
        if hasattr(self, 'queryset'):
            return self.queryset
        return self.model.objects

    def get_serializer_class(self):
        return class_registry.get_class(self.get_name())

    def get_name(self):
        return self.name

    def to_json(self, data, **kwargs):
        return json.dumps(data, **kwargs)

    def build_jsonapi_data(self, resource=None, resources=None):
        to_serialize = resource
        many = False
        if resources:
            to_serialize = resources
            many = True
        serializer = self.get_serializer_class()
        return serialize(self.get_name(), to_serialize, many=many, serializer=serializer)


class PostResource(Resource):
    name = 'posts'
    model = Post

