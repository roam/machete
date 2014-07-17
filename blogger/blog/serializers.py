# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from marshmallow import fields, class_registry
from machete.serializers import (ContextSerializer, LinksField,
                                 ForeignKeyIdField, ManyToManyIdField,
                                 AutoHrefField)


class TagSerializer(ContextSerializer):
    TYPE = 'tags'
    id = fields.String(attribute='name')
    links = LinksField({
        'posts': ManyToManyIdField(relation_type='posts', model='blog.Post'),
    })


class AuthorSerializer(ContextSerializer):
    TYPE = 'people'
    #href = AutoHrefField('people')

    class Meta:
        additional = ('id', 'name',)


class CommentSerializer(ContextSerializer):
    TYPE = 'comments'
    #href = AutoHrefField('comments')
    links = LinksField({
        'author': ForeignKeyIdField(relation_type='people', model='blog.Person'),
        'post': ForeignKeyIdField(relation_type='posts', model='blog.Post'),
    })
    class Meta:
        additional = ('id', 'content', 'commenter',)


class PostSerializer(ContextSerializer):
    TYPE = 'posts'
    #href = AutoHrefField('posts')
    links = LinksField({
        'author': ForeignKeyIdField(relation_type='people', model='blog.Person'),
        'tags': ManyToManyIdField(pk_field='name', model='blog.Tag'),
        'comments': ManyToManyIdField(method='approved_comments', model='blog.Comment')
    })
    class Meta:
        additional = ('id', 'title', 'content',)

    def approved_comments(self, obj, context=None):
        return obj.get_approved_comments()


class_registry.register('tags', TagSerializer)
class_registry.register('people', AuthorSerializer)
class_registry.register('comments', CommentSerializer)
class_registry.register('posts', PostSerializer)
