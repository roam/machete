# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from machete.urls import patterns_for
from .endpoints import Posts, People, Comments, Tags


urlpatterns = patterns_for(Posts)
urlpatterns += patterns_for(Posts, 'comments', to_many=True)
urlpatterns += patterns_for(Comments)
urlpatterns += patterns_for(Tags)
urlpatterns += patterns_for(People)
