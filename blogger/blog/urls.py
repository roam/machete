# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from django.views.decorators.csrf import csrf_exempt

from django.conf.urls import patterns, url

from .views import PostsEndpoint

urlpatterns = patterns('blog.views',
    url(r'^posts$', csrf_exempt(PostsEndpoint.as_view()), name="api_posts"),
    url(r'^posts/(?P<pks>([\w|\-|,]+))$', csrf_exempt(PostsEndpoint.as_view()), name="api_posts_detail"),
    url(r'^comments$', csrf_exempt(PostsEndpoint.as_view()), name="api_comments"),
    url(r'^comments/(?P<pks>([\w|\-|,]+))$', csrf_exempt(PostsEndpoint.as_view()), name="api_comments_detail"),
    url(r'^tags$', csrf_exempt(PostsEndpoint.as_view()), name="api_tags"),
    url(r'^tags/(?P<pks>([\w|\-|,]+))$', csrf_exempt(PostsEndpoint.as_view()), name="api_tags_detail"),
    url(r'^people$', csrf_exempt(PostsEndpoint.as_view()), name="api_people"),
    url(r'^people/(?P<pks>([\w|\-|,]+))$', csrf_exempt(PostsEndpoint.as_view()), name="api_people_detail"),
)
