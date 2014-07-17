# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from machete.endpoints import Endpoint

from .forms import PostForm
from .models import Post
from .serializers import PostSerializer  # Import needed to ensure the serializer has been registered


#def post_details(request, ids):
#    print(resource_url_template('post_details', '{posts.posts}'))

class PostsEndpoint(Endpoint):
    resource_name = 'posts'
    model = Post
    form_class = PostForm
    url_name_detail = 'posts_detail'
