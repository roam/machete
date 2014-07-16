# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from django.views.decorators.csrf import csrf_exempt

from django.conf.urls import patterns, include, url

from .endpoints import PostEndpoint
from .views import PostsView

urlpatterns = patterns('blog.views',
    url(r'^theposts$', csrf_exempt(PostsView.as_view()), name="the_posts"),
    url(r'^theposts/(?P<pks>([\w|\-|,]+))$', csrf_exempt(PostsView.as_view()), name="the_posts_detail"),
    url(r'^myposts$', PostEndpoint.as_view(), name="posts"),
    url(r'^myposts/(?P<ids>([\w|\-|,]+))$', PostEndpoint.as_view(), name="posts_detail"),
    url(r'^posts/(?P<ids>([\w|\-|,]+))$', 'post_details', name="post_details"),
    url(r'^posts-details/(?P<ids>([\w|\-|,]+))$', 'post_nested_details', name="post_nested_details"),
    url(r'^zeposts$', 'posts', name="posts"),
    url(r'^zeposts/(?P<ids>([\w|\-|,]+))$', 'posts', name="posts_detail"),
)
