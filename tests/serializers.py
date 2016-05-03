# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from machete.vendor.marshmallow import fields, class_registry
from machete.serializers import (ContextSerializer, LinksField, ToOneIdField,
                                 ToManyIdField, AutoHrefField)

from .models import Post


class TagSerializer(ContextSerializer):
    TYPE = 'tags'
    id = fields.String(attribute='name')
    links = LinksField({
        'posts': ToManyIdField(relation_type='posts', model='blog.Post'),
    })


class AuthorSerializer(ContextSerializer):
    TYPE = 'people'
    links = LinksField({
        'posts': ToManyIdField(relation_type='posts', model='blog.Post', attribute='post_set'),
    })
    #href = AutoHrefField('people')

    class Meta:
        additional = ('id', 'name',)


class CommentSerializer(ContextSerializer):
    TYPE = 'comments'
    #href = AutoHrefField('comments')
    links = LinksField({
        'author': ToOneIdField(relation_type='people', model='blog.Person'),
        'post': ToOneIdField(relation_type='posts', model='blog.Post'),
    })
    class Meta:
        additional = ('id', 'content', 'commenter',)


class PostSerializer(ContextSerializer):
    TYPE = 'posts'
    #href = AutoHrefField('posts')
    links = LinksField({
        'author': ToOneIdField(relation_type='people', model='blog.Person'),
        'tags': ToManyIdField(pk_field='name', model='blog.Tag'),
        'comments': ToManyIdField(method='approved_comments', model='blog.Comment')
    })
    class Meta:
        model = Post

    def approved_comments(self, obj, context=None):
        return obj.get_approved_comments()


class_registry.register('tags', TagSerializer)
class_registry.register('people', AuthorSerializer)
class_registry.register('comments', CommentSerializer)
class_registry.register('posts', PostSerializer)
