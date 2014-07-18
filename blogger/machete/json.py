# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

import json
import decimal
import datetime


__all__ = ['StandardizedJSONEncoder', 'loads', 'dumps']


class StandardizedJSONEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, datetime.datetime):
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
