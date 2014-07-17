# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from machete.endpoints import Endpoint, GetEndpoint

from .forms import PostForm
from .models import Post, Person, Comment, Tag
from .serializers import PostSerializer  # Import needed to ensure the serializer has been registered


class Posts(Endpoint):
    resource_name = 'posts'
    model = Post
    form_class = PostForm


class People(GetEndpoint):
    resource_name = 'people'
    model = Person


class Comments(GetEndpoint):
    resource_name = 'comments'
    model = Comment


class Tags(GetEndpoint):
    resource_name = 'tags'
    model = Tag
