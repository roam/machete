# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from django.views.decorators.csrf import csrf_exempt

from django.conf.urls import patterns, include, url

from .views import PostsEndpoint

urlpatterns = patterns('blog.views',
    url(r'^posts$', csrf_exempt(PostsEndpoint.as_view()), name="posts"),
    url(r'^posts/(?P<pks>([\w|\-|,]+))$', csrf_exempt(PostsEndpoint.as_view()), name="posts_detail"),
)
