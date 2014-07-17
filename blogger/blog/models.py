# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from django.db import models


class Tag(models.Model):
    name = models.SlugField(unique=True)


class Person(models.Model):
    name = models.CharField(max_length=200)


class Post(models.Model):
    title = models.CharField(max_length=300)
    content = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True, null=True)
    author = models.ForeignKey(Person)

    def get_approved_comments(self):
        return self.comments.filter(approved=True)

    approved_comments = property(get_approved_comments)


class Comment(models.Model):
    content = models.TextField()
    commenter = models.CharField(max_length=200)
    post = models.ForeignKey(Post, related_name='comments')
    author = models.ForeignKey(Person, blank=True, null=True)
    approved = models.BooleanField(default=False)
