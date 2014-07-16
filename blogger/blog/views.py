# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from machete.views import JsonApiEndpoint

from .forms import PostForm
from .models import Post


#def post_details(request, ids):
#    print(resource_url_template('post_details', '{posts.posts}'))

class PostsView(JsonApiEndpoint):
    resource_name = 'posts'
    model = Post
    form_class = PostForm
    url_name_detail = 'posts_detail'
