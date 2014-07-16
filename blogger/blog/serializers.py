# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from marshmallow import Serializer, fields, class_registry
from machete.serializers import (ContextSerializer, LinksField,
                                 ForeignKeyIdField, ManyToManyIdField)

from .models import Author, Tag, Comment


class TagSerializer(Serializer):
    name = fields.String()

class_registry.register('tags', TagSerializer)


class AuthorSerializer(ContextSerializer):
    href = fields.Method('get_url')

    class Meta:
        additional = ('id', 'name',)

    def get_url(self, obj):
        return '/hey/there/' + obj.name + '/'


class_registry.register('people', AuthorSerializer)


class CommentSerializer(ContextSerializer):
    links = LinksField({
        'author': ForeignKeyIdField(model=Author, debug='commentauthor'),
    })
    class Meta:
        additional = ('id', 'content', 'commenter',)


class_registry.register('comments', CommentSerializer)


class PostSerializer(ContextSerializer):
    links = LinksField({
        'author': ForeignKeyIdField(model=Author, relation_type='people', serializer='people'),
        'tags': ManyToManyIdField(model=Tag, pk_field='name', serializer='tags'),
        'comments': ManyToManyIdField(model=Comment, serializer='comments')
    })
    class Meta:
        additional = ('id', 'title', 'content',)


class_registry.register('posts', PostSerializer)


class PostNestedCommentsSerializer(ContextSerializer):
    links = LinksField({
        'author': ForeignKeyIdField(model=Author, relation_type='people', serializer='people'),
        'tags': ManyToManyIdField(model=Tag, pk_field='name', serializer='tags'),
        'comments': ManyToManyIdField(model=Comment, serializer='comments')
    })
    class Meta:
        additional = ('id', 'title', 'content',)


class_registry.register('nestedposts', PostNestedCommentsSerializer)
