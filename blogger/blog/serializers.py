# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from marshmallow import Serializer, fields, class_registry
from machete.serializers import (ContextSerializer, LinksField,
                                 ForeignKeyIdField, ManyToManyIdField,
                                 AutoHrefField)

from .models import Author, Tag, Comment


class TagSerializer(Serializer):
    name = fields.String()


class AuthorSerializer(ContextSerializer):
    href = AutoHrefField('people')

    class Meta:
        additional = ('id', 'name',)


class CommentSerializer(ContextSerializer):
    href = AutoHrefField('comments')
    links = LinksField({
        'author': ForeignKeyIdField(model=Author, debug='commentauthor'),
    })
    class Meta:
        additional = ('id', 'content', 'commenter',)


class PostSerializer(ContextSerializer):
    href = AutoHrefField('posts')
    links = LinksField({
        'author': ForeignKeyIdField(model=Author, relation_type='people', serializer='people'),
        'tags': ManyToManyIdField(model=Tag, pk_field='name', serializer='tags'),
        'comments': ManyToManyIdField(model=Comment, serializer='comments')
    })
    class Meta:
        additional = ('id', 'title', 'content',)


class_registry.register('tags', TagSerializer)
class_registry.register('people', AuthorSerializer)
class_registry.register('comments', CommentSerializer)
class_registry.register('posts', PostSerializer)
