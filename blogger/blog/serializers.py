# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from marshmallow import Serializer, fields, class_registry
from machete.serializers import (ContextSerializer, LinksField,
                                 ForeignKeyIdField, ManyToManyIdField,
                                 AutoHrefField)


class TagSerializer(Serializer):
    name = fields.String()


class AuthorSerializer(ContextSerializer):
    #href = AutoHrefField('people')

    class Meta:
        additional = ('id', 'name',)


class CommentSerializer(ContextSerializer):
    #href = AutoHrefField('comments')
    links = LinksField({
        'author': ForeignKeyIdField(relation_type='people'),
    })
    class Meta:
        additional = ('id', 'content', 'commenter',)


class PostSerializer(ContextSerializer):
    href = AutoHrefField('posts')
    links = LinksField({
        'author': ForeignKeyIdField(relation_type='people'),
        'tags': ManyToManyIdField(pk_field='name'),
        'comments': ManyToManyIdField(method='approved_comments')
    })
    class Meta:
        additional = ('id', 'title', 'content',)

    def approved_comments(self, obj, context=None):
        return obj.get_approved_comments()


class_registry.register('tags', TagSerializer)
class_registry.register('people', AuthorSerializer)
class_registry.register('comments', CommentSerializer)
class_registry.register('posts', PostSerializer)
