# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)


class JsonApiError(Exception):

    def __init__(self, *args, **kwargs):
        super(JsonApiError, self).__init__(*args, **kwargs)


class MissingRequestBody(JsonApiError):
    pass


class InvalidDataFormat(JsonApiError):
    pass


class IdMismatch(JsonApiError):
    pass


class FormValidationError(JsonApiError):

    def __init__(self, *args, **kwargs):
        self.form = kwargs.pop('form', None)
        super(FormValidationError, self).__init__(*args, **kwargs)
