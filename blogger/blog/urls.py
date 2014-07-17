# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from django.conf.urls import patterns, url

from .views import Posts, People, Comments, Tags

posts = Posts.endpoint()
post_comments = Posts.endpoint('comments')
comments = Comments.endpoint()
tags = Tags.endpoint()
people = People.endpoint()

urlpatterns = patterns('blog.views',
    url(r'^posts$', posts, name="api_posts"),
    url(r'^posts/(?P<pks>([\w|\-|,]+))$', posts, name="api_posts_detail"),
    url(r'^posts/(?P<pks>([\w|\-|,]+))/links/comments$', post_comments, name="api_posts_comments"),
    url(r'^posts/(?P<pks>([\w|\-|,]+))/links/comments/(?P<rel_pks>([\w|\-|,]+))$', post_comments, name="api_posts_comments_detail"),
    url(r'^comments$', comments, name="api_comments"),
    url(r'^comments/(?P<pks>([\w|\-|,]+))$', comments, name="api_comments_detail"),
    url(r'^tags$', tags, name="api_tags"),
    url(r'^tags/(?P<pks>([\w|\-|,]+))$', tags, name="api_tags_detail"),
    url(r'^people$', people, name="api_people"),
    url(r'^people/(?P<pks>([\w|\-|,]+))$', people, name="api_people_detail"),
)
