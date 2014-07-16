# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

import json
from collections import defaultdict, namedtuple
import functools

from django.db import models
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .forms import PostForm
from .models import Post, Comment, Author, Tag
from .serializers import serialize, PostSerializer, Context, PostNestedCommentsSerializer, serialization_context, init_serialization_context, resource_url_template


def post_details(request, ids):
    print(resource_url_template('post_details', '{posts.posts}'))
    return serialize_posts(ids, PostSerializer)

def post_nested_details(request, ids):
    return serialize_posts(ids, PostNestedCommentsSerializer)

def serialize_posts(ids, serializer):
    posts = Post.objects.filter(pk__in=ids.split(','))
    data = serialize('posts', posts, many=True)
    return HttpResponse(json.dumps(data, indent=2), content_type='application/json')


ResourceToModel = namedtuple('ResourceToModel', 'resource model')


class Response(object):

    def __init__(self, resources, name=None, compound=False):
        self.name = name
        self.resources = resources
        self.compound = compound

    def serialize(self, many=False):
        return serialize(self.name, self.resources, many=many, compound=self.compound)


def jsonapi(func=None, name=None, methods=None, reply_type=None, indent=0):
    the_name = name
    def decorator(view):
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            if not the_name:
                name = view.__name__
            else:
                name = the_name
            ids = kwargs.get('ids')
            if ids:
                ids = ids.split(',')
                kwargs['ids'] = ids
            else:
                ids = None
            many = ids is None or len(ids) > 1
            body = request.body
            request_resources = None
            request_resource = None
            if body:
                body = json.loads(body)
                request_resource = body.get(name)
                if isinstance(request_resource, list):
                    request_resources = request_resource
                    request_resource = None
                else:
                    request_resources = [request_resource]
            status = 200
            if request.method == 'POST':
                status = 201
            setattr(request, 'json', body)
            setattr(request, 'resource', request_resource)
            setattr(request, 'resources', request_resources)
            try:
                response = view(request, *args, **kwargs)
                if not isinstance(response, Response):
                    response = Response(response)
                if not response.name:
                    response.name = name
                do_many = many
                if request.resources:
                    do_many = len(request.resources) > 1
                data = response.serialize(many=do_many)
            except Failed as error:
                status = error.status
                data = error.serialize()
            return HttpResponse(json.dumps(data, indent=indent), content_type='application/json', status=status)
        return wrapper
    if func:
        return decorator(func)
    return decorator


class Failed(Exception):

    def __init__(self, message, status=500):
        self.status = status
        super(Failed, self).__init__(message)

    def serialize(self):
        return {}


class CreateFailed(Failed):

    def __init__(self, message, failures, status=500):
        super(CreateFailed, self).__init__(message, status=status)
        self.failures = failures


@csrf_exempt
@jsonapi(name='posts')
def posts(request, ids=None):
    qs = Post.objects.all()
    if request.method == 'GET':
        return get(qs, ids)
    if request.method == 'POST':
        return [i.model for i in create(request, PostForm)]
    if request.method == 'PUT':
        return [i.model for i in update('posts', request, ids, qs, PostForm)]


def get(qs, ids):
    nr_ids = len(ids)
    if nr_ids > 1:
        qs = qs.filter(pk__in=ids)
        return qs
    elif nr_ids == 1:
        return qs.get(pk=ids[0])
    return qs


def update(name, request, ids, qs, form_class, raise_error=True, **form_kwargs):
    updated, failed = update_resources(name, request.resources, ids, qs, form_class, **form_kwargs)
    if raise_error:
        if failed:
            raise CreateFailed('', failed, status=400)
        return updated
    return updated, failed


def update_resources(name, resources, ids, qs, form_class, **form_kwargs):
    updated = []
    failed = []
    for resource in resources:
        resource_id = resource.get('id')
        if not resource_id:
            if len(ids) > 1:
                raise Failed('Missing ids')
            else:
                resource_id = ids[0]
        if resource_id not in ids:
            raise Failed('Missing ids')
        print('RESOURCE_ID: %s' % resource_id)
        instance = qs.get(pk=resource_id)
        model, errors = update_resource(name, resource, instance, form_class, **form_kwargs)
        if errors:
            failed.append((resource, errors))
        else:
            updated.append(ResourceToModel(resource, model))
    return updated, failed


def update_resource(name, resource, instance, form_class, **form_kwargs):
    if not form_kwargs:
        form_kwargs = {}
    print(instance)
    original = serialize(name, instance, compound=False)
    merged = dict(original.items() + original.get('links', {}).items())
    data = dict(resource.items() + resource.get('links', {}).items())
    for field, value in data.items():
        if value is None:
            merged[field] = None
        else:
            merged[field] = value
    form_kwargs['data'] = data
    form_kwargs['instance'] = instance
    form = form_class(**form_kwargs)
    if form.is_valid():
        return form.save(), None
    return None, form.errors


def create(request, form_class, raise_error=True, **form_kwargs):
    created, failed = create_resources(request.resources, form_class, **form_kwargs)
    if raise_error:
        if failed:
            raise CreateFailed('', failed, status=400)
        return created
    return created, failed


def create_resources(resources, form_class, **form_kwargs):
    created = []
    failed = []
    for resource in resources:
        model, errors = create_resource(resource, form_class, **form_kwargs)
        if errors:
            failed.append((resource, errors))
        else:
            created.append(ResourceToModel(resource, model))
    return created, failed


def create_resource(resource, form_class, **form_kwargs):
    if not form_kwargs:
        form_kwargs = {}
    data = dict(resource.items() + resource.get('links', {}).items())
    form_kwargs['data'] = data
    form = form_class(**form_kwargs)
    if form.is_valid():
        return form.save(), None
    return None, form.errors
