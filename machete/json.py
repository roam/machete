# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

import json
import decimal
import datetime

from django.utils import timezone


__all__ = ['StandardizedJSONEncoder', 'loads', 'dumps']


class StandardizedJSONEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, datetime.datetime):
            if timezone.is_naive(o):
                o = timezone.make_aware(o, timezone.get_default_timezone())
            o = o.astimezone(timezone.utc)
            return o.strftime('%Y-%m-%dT%H:%M:%SZ')
        if isinstance(o, (datetime.date, datetime.time)):
            return o.isoformat()
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(StandardizedJSONEncoder, self).default(o)


def loads(o, **kwargs):
    return json.loads(o)


def dumps(data, **kwargs):
    if 'cls' not in kwargs:
        kwargs['cls'] = StandardizedJSONEncoder
    return json.dumps(data, **kwargs)
