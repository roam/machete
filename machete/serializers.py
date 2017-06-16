# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

import datetime
import threading
from collections import defaultdict, OrderedDict

from .vendor.marshmallow import serializer, Serializer, fields, class_registry
from django.db.models import ForeignKey, ManyToManyField
from django.core.exceptions import ImproperlyConfigured
from django.apps.registry import apps

from . import compat
from .urls import (get_resource_url_template, get_resource_detail_url,
                   to_absolute_url, create_resource_view_name)
from .json import dumps


threadlocal = threading.local()


class Registry(object):
    """
    Registry for serializers preventing multiple registrations for the
    same type.

    """

    def __init__(self):
        self.registry = {}

    def register(self, serializer_class, name=None):
        if not name:
            name = serializer_class.TYPE
        if name not in self.registry:
            self.registry[name] = True
            class_registry.register(name, serializer_class)

    def get_class(self, name):
        return class_registry.get_class(name)


registry = Registry()


def filter_fields(serializer, fields):
    meta = serializer.Meta
    if hasattr(meta, 'fields'):
        allowed = set(getattr(meta, 'fields'))
    else:
        allowed = [n for n, mapping in serializer._declared_fields.items()]
        if hasattr(meta, 'additional'):
            allowed = allowed + list(getattr(meta, 'additional'))
        allowed = set(allowed)
    return [f for f in fields if f in allowed]


class JsonApiSerializer(object):

    def __init__(self, name, compound=False, self_link=False):
        self.name = name
        self.compound = compound
        self.self_link = self_link

    def serialize(self, *args, **kwargs):
        externalized_caching = kwargs.pop('externalized_caching', False)
        if externalized_caching:
            return self._do_serialize(*args, **kwargs)
        setattr(threadlocal, 'cache', {})
        try:
            return self._do_serialize(*args, **kwargs)
        finally:
            delattr(threadlocal, 'cache')

    def _do_serialize(self, *args, **kwargs):
        serializer_class = kwargs.pop('serializer', None)
        if not serializer_class:
            serializer_class = self.get_serializer_class(self.name)
        if not 'context' in kwargs:
            kwargs['context'] = {}
        context = kwargs['context']
        if 'only' in kwargs:
            if kwargs['only']:
                kwargs['only'] = filter_fields(serializer_class, kwargs['only'])
        serializer = serializer_class(*args, **kwargs)
        serialized_data = serializer.data
        ids_by_type, ids_by_name = self.collect_ids(serialized_data, serializer)
        require_links = ['%s.%s' % (self.name, k) for k in ids_by_name.keys()]
        linked_links = []
        linked = None
        if self.compound:
            linked, linked_links = self.serialize_linked(serializer, ids_by_type)
        links = self.compile_links(require_links, context)
        linked_links = self.compile_links(linked_links, context, self.name + '.')
        links = dict(linked_links.items() + links.items())
        if self.self_link and not self.name in links:
            links[self.name] = {
                'href': serializer.get_detail_url_template(self.name, context),
                'type': serializer.TYPE
            }
        data = OrderedDict()
        if links:
            data['links'] = links
        data[self.name] = serialized_data
        if linked:
            data['linked'] = linked
        return data

    def compile_links(self, paths, context, serializer_path_prefix=None):
        if not serializer_path_prefix:
            serializer_path_prefix = ''
        links = {}
        for path in paths:
            s_path = serializer_path_prefix + path
            s_class = self.get_serializer_class(s_path)
            s = s_class()
            links[path] = {
                'href': s.get_detail_url_template(path, context),
                'type': s.TYPE
            }
        return links

    def get_serializer_class(self, path):
        parts = path.split('.')
        cls = class_registry.get_class(parts[0])
        for part in parts[1:]:
            links = cls().fields.get('links')
            if not links:
                raise ImproperlyConfigured('Could not find serializer for '
                                           '%s (path: %s)' % (part, path))
            relation_field = links.link_fields.get(part)
            if not relation_field:
                raise ImproperlyConfigured('Relation %s not included as link '
                                           '(path: %s)' % (part, path))
            rel_type = relation_field.get_relation_type()
            cls = class_registry.get_class(rel_type)
        return cls

    def serialize_linked(self, serializer, ids_by_type):
        linked = {}
        field = serializer.fields.get('links')
        require_link = []
        if not field:
            return linked, require_link
        for field_name, relationship_field in field.link_fields.items():
            rel_type = relationship_field.get_relation_type()
            ids = ids_by_type.get(rel_type)
            if not ids:
                continue
            try:
                instances = relationship_field.get_instances(ids)
            except RelationIdField.Misconfigured:
                s_name = serializer.__class__.__name__
                msg_data = {'field_name': field_name, 'serializer': s_name}
                msg = ('Specify a model or queryset for RelationIdField '
                       '"%(field_name)s" in serializer %(serializer)s or '
                       'prevent the construction of compound '
                       'documents.') % msg_data
                raise ImproperlyConfigured(msg)
            rel_serializer_class = self.get_serializer_class(rel_type)
            rel_serializer = rel_serializer_class(instances, many=True)
            serialized_data = rel_serializer.data
            linked[rel_type] = serialized_data
            # Now collect ids for "linked" links so we know which ones require
            # a URL template (no embedded of links in "linked" for now)
            x, sub_by_name = self.collect_ids(serialized_data, rel_serializer)
            for name, ids in sub_by_name.items():
                require_link.append('%s.%s' % (field_name, name))
        return linked, require_link

    def collect_ids(self, data, serializer):
        link_fields = serializer.fields.get('links')
        if not link_fields:
            return {}, {}
        link_fields = link_fields.link_fields
        if not isinstance(data, list):
            data = [data]
        by_type = defaultdict(set)
        by_name = defaultdict(set)
        for item in data:
            links = item.get('links', {})
            if not links:
                continue
            for name, value in links.items():
                relation_type = link_fields.get(name).get_relation_type()
                if value is None:
                    continue
                if isinstance(value, basestring):
                    value = [value]
                by_type[relation_type] |= set(value)
                by_name[name] |= set(value)
        return by_type, by_name


def serialize_to_json(name, *args, **kwargs):
    data = serialize(name, *args, **kwargs)
    return dumps(data)


def serialize(name, *args, **kwargs):
    compound = kwargs.pop('compound', False)
    self_link = kwargs.pop('self_link', False)
    return JsonApiSerializer(name, compound=compound, self_link=self_link).serialize(*args, **kwargs)


class UtcDateTime(fields.Raw):

    def format(self, value):
        if isinstance(value, datetime.datetime):
            return value.strftime('%Y-%m-%dT%H:%M:%SZ')
        return value.strftime('%Y-%m-%d')


class NestedManyToMany(fields.Nested):

    def get_value(self, key, obj):
        return getattr(obj, key).all()


class RelationIdField(fields.Raw):
    """
    Maps a relationship to an id.

    - Pass the ``pk_field`` in case the id doesn't map to ``pk``
    - Pass ``relation_type`` in case the field's name doesn't match the name
      of the relationshp
    - Pass ``attribute`` to use an attribute of the parent object (e.g. pass
      ``approved_comments`` from ``Post`` to only include the approved
      comments of a blog post)
    - Pass a method name of the serializer as ``method`` to invoke the method
      allowing for the parent object and context as parameters.

    """

    class Misconfigured(Exception):
        pass

    def __init__(self, *args, **kwargs):
        self.pk_field = kwargs.pop('pk_field', 'pk')
        self.relation_type = kwargs.pop('relation_type', None)
        self.method = kwargs.pop('method', None)
        self.model = kwargs.pop('model', None)
        self.queryset = kwargs.pop('queryset', None)
        self.use_caching = kwargs.pop('use_caching', False)
        super(RelationIdField, self).__init__(*args, **kwargs)

    @property
    def cache(self):
        return getattr(threadlocal, 'cache', None)

    def get_instances(self, pks):
        if not self.use_caching:
            return self.get_queryset(pks).all()
        non_cached_pks = []
        rel_type = self.get_relation_type()
        cache = self.cache.get(rel_type, None)
        if not cache:
            cache = {}
        for pk in pks:
            if not cache.get('%s' % pk):
                non_cached_pks.append('%s' % pk)
        if non_cached_pks:
            non_cached = self.get_queryset(non_cached_pks).all()
            for item in non_cached:
                cache['%s' % item.pk] = item
            self.cache[rel_type] = cache
        results = [cache.get('%s' % pk) for pk in pks]
        return results

    def get_queryset(self, pks):
        queryset = None
        if self.queryset is not None:
            queryset = self.queryset
            if hasattr(queryset, '_clone'):
                queryset = queryset._clone()
        elif self.model is not None:
            if isinstance(self.model, basestring):
                app, model_name = self.model.split('.')
                queryset = apps.get_model(app, model_name).objects
            else:
                queryset = self.model.objects
        else:
            raise self.Misconfigured('missing_model_queryset')
        filter = {'%s__in' % self.pk_field: pks}
        return queryset.filter(**filter)

    def get_relation_type(self):
        relation_type = self.relation_type
        if not relation_type:
            return self.name
        return relation_type

    def get_related(self, key, obj):
        if self.method:
            method = getattr(self.parent, self.method)
            return method(obj, self.parent.context)
        related = self.get_value(key, obj)
        if callable(related) and not getattr(related, 'do_not_call_in_templates', False):
            return related()
        return related


class ToManyIdField(RelationIdField):

    def __init__(self, *args, **kwargs):
        self.assume_prefetched = kwargs.pop('assume_prefetched', False)
        super(ToManyIdField, self).__init__(*args, **kwargs)

    def output(self, key, obj):
        related = self.get_related(key, obj)
        if self.assume_prefetched:
            return ['%s' % getattr(i, self.pk_field) for i in related.all()]
        if hasattr(related, 'values_list'):
            values = related.values_list(self.pk_field, flat=True)
            values = ['%s' % pk for pk in values]
            return values if values else None
        return None


class ToOneIdField(RelationIdField):

    def __init__(self, *args, **kwargs):
        self.simple_id_field = kwargs.pop('simple_id_field', None)
        super(ToOneIdField, self).__init__(*args, **kwargs)

    def output(self, key, obj):
        value = None
        if self.simple_id_field:
            value = getattr(obj, self.simple_id_field, None)
        else:
            related = self.get_related(key, obj)
            if related:
                value = getattr(related, self.pk_field)
        if value is not None:
            return '%s' % value
        return None


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
            link_field.parent = self.parent
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
        # TODO There's still an issue with nested components in which
        # the context isn't passed
        ids = [obj.pk]
        url = get_resource_detail_url(self.resource_name, ids)
        return to_absolute_url(url, self.parent.context.get('request'))


class Options(serializer.SerializerOpts):

    def __init__(self, meta):
        model = getattr(meta, 'model', None)
        if model:
            self.model = model
            additional = getattr(meta, 'additional', None)
            additional = [] if not additional else list(additional)
            opts = model._meta
            for name in compat.get_all_field_names(opts):
                field, model, direct, m2m = compat.get_field_by_name(opts, name)
                link = isinstance(field, (ForeignKey, ManyToManyField,))
                if direct and not link:
                    additional.append(name)
            setattr(meta, 'additional', additional)
        super(Options, self).__init__(meta)


class ContextSerializer(Serializer):
    OPTIONS_CLASS = Options

    def get_detail_url_template(self, path, context):
        import urllib
        name = create_resource_view_name(self.TYPE)
        kwargs = self.get_detail_url_template_kwargs(path, context)
        relative = get_resource_url_template(name, '{%s}' % path, kwargs=kwargs)
        url = to_absolute_url(relative, context.get('request'))
        return urllib.unquote(url).decode('utf-8')

    def get_detail_url_template_kwargs(self, path, context, **kwargs):
        return kwargs

    def _update_data(self):
        super(ContextSerializer, self)._update_data()
        data = self._data
        if self.many:
            items = data
        else:
            items = [data]
        for item in items:
            if 'id' in item:
                pk = item.get('id', None)
                if pk:
                    item['id'] = '%s' % pk


ContextSerializer.TYPE_MAPPING.update({
    datetime.datetime: fields.Raw,
    datetime.date: fields.Raw,
    datetime.time: fields.Raw
})
