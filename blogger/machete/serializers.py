# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from collections import defaultdict

from marshmallow import Serializer, fields, class_registry
from django.db.models import get_model
from django.core.exceptions import ImproperlyConfigured

from .urls import (get_resource_url_template, get_resource_detail_url,
                   to_absolute_url, create_resource_view_name)


class JsonApiSerializer(object):

    def __init__(self, name, compound=False):
        self.name = name
        self.compound = compound

    def serialize(self, *args, **kwargs):
        serializer_class = kwargs.pop('serializer', None)
        if not serializer_class:
            serializer_class = self.get_serializer_class(self.name)
        if not 'context' in kwargs:
            kwargs['context'] = {}
        context = kwargs['context']
        serializer = serializer_class(*args, **kwargs)
        serialized_data = serializer.data
        data = {self.name: serialized_data}
        ids_by_type, ids_by_name = self.collect_ids(serialized_data, serializer)
        require_links = ['%s.%s' % (self.name, k) for k in ids_by_name.keys()]
        linked_links = []
        if self.compound:
            linked, linked_links = self.serialize_linked(serializer, ids_by_type)
            if linked:
                data['linked'] = linked
        links = self.compile_links(require_links, context)
        linked_links = self.compile_links(linked_links, context, self.name + '.')
        links = dict(linked_links.items() + links.items())
        if links:
            data['links'] = links
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
        for field_name, relationship_field in field.link_fields.items():
            rel_type = relationship_field.get_relation_type()
            ids = ids_by_type.get(rel_type)
            if not ids:
                continue
            try:
                instances = relationship_field.get_queryset(ids)
            except RelationIdField.Misconfigured:
                s_name = serializer.__class__.__name__
                msg_data = {'field_name': field_name, 'serializer': s_name}
                msg = ('Specify a model or queryset for RelationIdField '
                       '"%(field_name)s" in serializer %(serializer)s or '
                       'prevent the construction of compound '
                       'documents.') % msg_data
                raise ImproperlyConfigured(msg)
            rel_serializer_class = self.get_serializer_class(rel_type)
            rel_serializer = rel_serializer_class(instances.all(), many=True)
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



def serialize(name, *args, **kwargs):
    compound = kwargs.pop('compound', False)
    return JsonApiSerializer(name, compound=compound).serialize(*args, **kwargs)


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
        super(RelationIdField, self).__init__(*args, **kwargs)

    def get_queryset(self, pks):
        queryset = None
        if self.queryset is not None:
            queryset = self.queryset
            if hasattr(queryset, '_clone'):
                queryset = queryset._clone()
        elif self.model is not None:
            if isinstance(self.model, basestring):
                app, model_name = self.model.split('.')
                queryset = get_model(app, model_name).objects
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
        if callable(related):
            return related()
        return related


class ManyToManyIdField(RelationIdField):

    def output(self, key, obj):
        related = self.get_related(key, obj)
        if related:
            values = related.values_list(self.pk_field, flat=True)
            values = ['%s' % pk for pk in values]
            return values if values else None
        return None


class ForeignKeyIdField(RelationIdField):

    def output(self, key, obj):
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
        ids = [obj.pk]
        url = get_resource_detail_url(self.resource_name, ids)
        return to_absolute_url(url, self.parent.context.get('request'))


class ContextSerializer(Serializer):

    def get_detail_url_template(self, path, context):
        import urllib
        name = create_resource_view_name(self.TYPE)
        relative = get_resource_url_template(name, '{%s}' % path)
        url = to_absolute_url(relative, context.get('request'))
        return urllib.unquote(url).decode('utf-8')
