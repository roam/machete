# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

import threading
from collections import MutableMapping, defaultdict

from marshmallow import Serializer, fields, class_registry

from .urls import get_resource_detail_url, to_absolute_url


threadlocal = threading.local()


def serialize(name, *args, **kwargs):
    compound = kwargs.pop('compound', False)
    serializer_class = kwargs.pop('serializer', None)
    if not serializer_class:
        serializer_class = class_registry.get_class(name)
    if not 'context' in kwargs:
        kwargs['context'] = {}
    init_serialization_context()
    serializer = serializer_class(*args, **kwargs)
    embedded = serializer.data
    context = serialization_context()
    current_ids_by_field = context.ids_by_field.copy()
    #current_ids_by_type = context.ids_by_type.copy()
    data = {name: embedded}
    #links = {}
    if compound:
        linked = {}
        sub_kwargs = kwargs.copy()
        sub_kwargs['many'] = True
        for attribute, ids in current_ids_by_field.items():
            field = serializer.fields['links'].field_by_relation_type(attribute)
            instances = field.get_instances(ids)
            init_serialization_context()
            linked[field.get_relation_type()] = field.get_serializer()(instances, **sub_kwargs).data
        data['linked'] = linked
    return data


class Context(MutableMapping):

    def __init__(self, values=None):
        self.ctx = values.copy() if values else {}
        self.ids_by_field = defaultdict(set)
        self.ids_by_type = defaultdict(set)

    def __getitem__(self, key):
        return self.ctx[key]

    def __setitem__(self, key, value):
        self.ctx[key] = value

    def __delitem__(self, key):
        self.ctx.pop(key)

    def __iter__(self):
        return self.ctx.keys()

    def __len__(self):
        return len(self.ctx)

    def collect_ids(self, ids, field_name, field_type):
        id_set = set(ids)
        self.ids_by_field[field_name] |= id_set
        self.ids_by_type[field_type] |= id_set


def init_serialization_context():
    setattr(threadlocal, 'context', Context())

def serialization_context():
    if not hasattr(threadlocal, 'context'):
        setattr(threadlocal, 'context', Context())
    return getattr(threadlocal, 'context')


class NestedManyToMany(fields.Nested):

    def get_value(self, key, obj):
        return getattr(obj, key).all()


class RelationIdField(fields.Raw):

    def __init__(self, *args, **kwargs):
        self.model_cls = kwargs.pop('model', None)
        self.qs = kwargs.pop('qs', None)
        self.pk_field = kwargs.pop('pk_field', 'pk')
        self.relation_type = kwargs.pop('relation_type', None)
        self.serializer = kwargs.pop('serializer', None)
        super(RelationIdField, self).__init__(*args, **kwargs)

    def get_serializer(self, many=False):
        if isinstance(self.serializer, basestring):
            return class_registry.get_class(self.serializer)
        return self.serializer

    def get_queryset(self):
        if self.qs:
            return self.qs
        return self.model_cls.objects

    def get_instances(self, ids):
        filter = {'%s__in' % self.pk_field: ids}
        return self.get_queryset().filter(**filter)

    def get_model(self):
        model = self.model_cls
        if not model:
            model = self.qs._model
        if isinstance(model, basestring):
            from django.db.models import get_model
            app, name = model.split('.')
            model = get_model(app, name)
        else:
            app = model._meta.app_label
            name = model.__name__
        return model, app, name

    def get_relation_type(self):
        relation_type = self.relation_type
        if not relation_type:
            model, app, name = self.get_model()
            relation_type = '%ss' % name.lower()
        return relation_type

    def collect_ids(self, ids):
        model, app, name = self.get_model()
        model_id = app + '.' + name
        relation_type = self.get_relation_type()
        serialization_context().collect_ids(ids, relation_type, model_id)


class ManyToManyIdField(RelationIdField):

    def format(self, value):
        ids = list(value.values_list(self.pk_field, flat=True))
        self.collect_ids(ids)
        return ids


class ForeignKeyIdField(RelationIdField):

    def __init__(self, *args, **kwargs):
        self.debug = kwargs.pop('debug', None)
        super(ForeignKeyIdField, self).__init__(*args, **kwargs)

    def format(self, value):
        try:
            value = getattr(value, self.pk_field)
            if value is not None:
                self.collect_ids([value])
            return value
        except Exception as e:
            print(e)


class LinksField(fields.Raw):

    def __init__(self, link_fields, **kwargs):
        self.link_fields = link_fields
        super(LinksField, self).__init__(**kwargs)

    def field_by_relation_type(self, relation_type):
        for name, field in self.link_fields.items():
            if field.get_relation_type() == relation_type:
                return field
        return None

    def output(self, key, obj):
        links = {}
        for name, link_field in self.link_fields.items():
            link_field.name = name
            links[name] = link_field.output(name, obj)
        return links


class HrefField(fields.Method):

    def __init__(self, *args, **kwargs):
        if 'method_name' not in kwargs:
            kwargs['method_name'] = 'get_absolute_url'
        super(HrefField, self).__init__(*args, **kwargs)

    def output(self, key, obj):
        url = super(HrefField, self).output(key, obj)
        return to_absolute_url(url, self.parent.context.get('request'))


class AutoHrefField(fields.Raw):

    def __init__(self, resource_name, **kwargs):
        super(AutoHrefField, self).__init__(**kwargs)
        self.resource_name = resource_name

    def output(self, key, obj):
        ids = [obj.pk]
        url = get_resource_detail_url(self.resource_name, ids)
        return to_absolute_url(url, self.parent.context.get('request'))


class ContextSerializer(Serializer):
    pass
