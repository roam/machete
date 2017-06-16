# -*- coding: utf-8 -*-
# Backwards compatibility for Django. Details at
# https://docs.djangoproject.com/en/1.8/ref/models/meta/#migrating-old-meta-api
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

from itertools import chain


def get_all_field_names(opts):
    return list(set(chain.from_iterable(
        (field.name, field.attname) if hasattr(field, 'attname') else (field.name,)
        for field in opts.get_fields()
        if not (field.many_to_one and field.related_model is None)
    )))


def get_field_by_name(opts, name):
    field = opts.get_field(name)
    model = field.model
    direct = not field.auto_created or field.concrete
    return field, model, direct, field.many_to_many
