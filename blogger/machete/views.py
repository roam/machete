# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

import json

from django.views.generic import View
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.http import HttpResponse

from .serializers import serialize
from .exceptions import (JsonApiError, MissingRequestBody, InvalidDataFormat,
                         IdMismatch, FormValidationError)
from .utils import RequestContext, RequestWithResourceContext, pluck_ids


class WithFormMixin(object):

    def get_form_kwargs(self, **kwargs):
        return kwargs

    def get_form_class(self):
        return self.form_class

    def get_form(self, resource, instance=None):
        data = self.prepare_form_data(resource, instance)
        form_kwargs = {'data': data, 'instance': instance}
        form_kwargs = self.get_form_kwargs(**form_kwargs)
        form_class = self.get_form_class()
        if not form_class:
            raise ImproperlyConfigured('Missing form_class')
        return form_class(**form_kwargs)

    def prepare_form_data(self, resource, instance=None):
        if instance:
            original = self.serialize(instance, compound=False)
            original = original[self.get_resource_name()]
            merged = dict(original.items() + original.get('links', {}).items())
            data = dict(resource.items() + resource.get('links', {}).items())
            for field, value in data.items():
                if value is None:
                    merged[field] = None
                else:
                    merged[field] = value
            return merged
        return dict(resource.items() + resource.get('links', {}).items())


class PostMixin(object):
    url_name_detail = None
    url_name_list = None
    url_name = None

    def get_methods(self):
        return super(PostMixin, self).get_methods() + ['post']

    def post(self, request, *args, **kwargs):
        self.context = self.create_post_context(request)
        collection = False
        if self.context.many:
            data = self.create_resources(self.context.resources)
            collection = True
        else:
            data = self.create_resource(self.context.resource)
        return self.create_http_response(data, collection=collection)

    def create_post_context(self, request):
        resource, resources, many = self.extract_resources(request)
        if many:
            mode = 'create_multiple'
        else:
            mode = 'create'
        return RequestWithResourceContext(request, [], mode, resource, resources, many, status=201)

    def create_resources(self, resources):
        return [self.create_resource(r) for r in resources]

    def create_resource(self, resource):
        pass

    def postprocess_response(self, response, data, response_data, collection):
        if self.context.status != 201:
            return response
        pks = ','.join(pluck_ids(response_data, self.get_resource_name()))
        location = self.create_resource_url(pks)
        response['Location'] = location
        return response

    def create_resource_url(self, pks):
        kwargs = {self.pks_url_key: pks}
        return reverse(self.get_url_name('detail'), kwargs=kwargs)

    def get_url_name(self, url_type):
        if url_type == 'detail' and self.url_name_detail:
            return self.url_name_detail
        if url_type == 'list' and self.url_name_list:
            return self.url_name_list
        return self.url_name


class PostWithFormMixin(PostMixin, WithFormMixin):

    def create_resource(self, resource):
        form = self.get_form(resource)
        if form.is_valid():
            return form.save()
        raise FormValidationError('', form=form)


class PutMixin(object):

    def get_methods(self):
        return super(PutMixin, self).get_methods() + ['put']

    def put(self, request, *args, **kwargs):
        self.context = self.create_put_context(request)
        collection = False
        if self.context.many:
            changed_more, data = self.update_resources(self.context.resources)
            collection = True
        else:
            changed_more, data = self.update_resource(self.context.resource)
        if not changed_more:
            # > A server MUST return a 204 No Content status code if an update
            # > is successful and the client's current attributes remain up to
            # > date. This applies to PUT requests as well as POST and DELETE
            # > requests that modify links without affecting other attributes
            # > of a resource.
            return HttpResponse(status=204)
        return self.create_http_response(data, collection=collection, detect_changes=True)

    def create_put_context(self, request):
        pks = self.kwargs.get(self.pks_url_key, '')
        pks = pks.split(',') if pks else []
        resource, resources, many = self.extract_resources(request)
        if many:
            mode = 'update_multiple'
        else:
            mode = 'update'
        return RequestWithResourceContext(request, pks, mode, resource, resources, many, status=200)

    def update_resources(self, resources):
        updated = []
        changed = []
        for res in resources:
            changed_more, result = self.update_resource(res)
            updated.append(result)
            changed.append(changed_more)
        return any(changed), updated

    def update_resource(self, resource):
        pass


class PutWithFormMixin(PutMixin, WithFormMixin):

    def update_resource(self, resource):
        resource_id = resource['id']
        if resource_id not in self.context.pks:
            message = 'Id %s in request body but not in URL' % resource_id
            raise IdMismatch(message)
        filter = {self.get_pk_field(): resource_id}
        instance = self.get_queryset().get(**filter)
        form = self.get_form(resource, instance)
        if form.is_valid():
            model = form.save()
            return self.is_changed_besides(resource, model), model
        raise FormValidationError('', form=form)


class DeleteMixin(object):

    def get_methods(self):
        return super(DeleteMixin, self).get_methods() + ['delete']

    def delete(self, request, *args, **kwargs):
        self.context = self.create_delete_context(request)
        if self.context.pk:
            not_deleted = self.delete_resource()
        else:
            not_deleted = self.delete_resources()
        if not_deleted:
            # TODO Raise 404
            pass
        return HttpResponse(status=204)

    def create_delete_context(self, request):
        pks = self.kwargs.get(self.pks_url_key, '')
        pks = pks.split(',') if pks else []
        nr_pks = len(pks)
        if nr_pks == 1:
            mode = 'delete'
        else:
            mode = 'delete_multiple'
        return RequestContext(request, pks, mode)

    def delete_resources(self):
        return self.perform_delete(self.context.pks)

    def delete_resource(self):
        return self.perform_delete(self.context.pks)

    def perform_delete(self, pks):
        not_deleted = pks[:]
        filter = {'%s__in' % self.get_pk_field(): pks}
        for item in self.get_queryset().filter(**filter).iterator():
            # Fetch each item separately to actually trigger any logic
            # performed in the delete method (like implicit deletes)
            not_deleted.remove('%s' % item.pk)
            item.delete()
        return not_deleted


class GetJsonApiEndpoint(View):
    methods = ['get']
    pks_url_key = 'pks'
    pk_field = 'pk'
    queryset = None
    form_class = None

    def __init__(self, *args, **kwargs):
        super(GetJsonApiEndpoint, self).__init__(*args, **kwargs)
        self.context = None
        self.http_method_names = self.get_methods() + ['options']

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(GetJsonApiEndpoint, self).dispatch(request, *args, **kwargs)
        except Exception as error:
            print(error)
            import traceback
            print(traceback.format_exc())
            return self.handle_error(error)

    def options(self, request, *args, **kwargs):
        return HttpResponse(','.join(m.upper() for m in self.get_methods()))

    def get(self, request, *args, **kwargs):
        self.context = self.create_get_context(request)
        collection = False
        if self.context.pk:
            data = self.get_resource()
        else:
            data = self.get_resources()
            collection = True
        return self.create_http_response(data, collection=collection)

    def create_http_response(self, data, collection=False):
        if isinstance(data, HttpResponse):
            return data
        if isinstance(data, dict):
            response_data = data
        else:
            response_data = self.serialize(data, collection=collection)
        json_data = self.create_json(response_data, indent=2)
        status = self.context.status
        content_type = self.get_content_type()
        response = HttpResponse(json_data, content_type=content_type, status=status)
        return self.postprocess_response(response, data, response_data, collection)

    def serialize(self, data, collection=False, compound=False):
        return serialize(self.get_resource_name(), data, many=collection, compound=compound)

    def handle_error(self, error):
        error_object = {}
        status = 500
        if isinstance(error, FormValidationError):
            status = 400
        if isinstance(error, JsonApiError):
            error_object['message'] = '%s' % error
            return HttpResponse(self.create_json({'errors': error_object}), status=status)
        raise error

    def postprocess_response(self, response, data, response_data, collection):
        return response

    def get_resource(self):
        filter = {self.get_pk_field(): self.context.pk}
        return self.get_queryset().get(**filter)

    def get_resources(self):
        qs = self.get_queryset()
        if self.context.pks:
            filter = {'%s__in' % self.get_pk_field(): self.context.pks}
            qs = qs.filter(**filter)
        return qs

    def is_changed_besides(self, resource, model):
        # TODO Perform simple diff of serialized model with resource
        return False

    def get_pk_field(self):
        return self.pk_field

    def get_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        if self.queryset is not None:
            queryset = self.queryset
            if hasattr(queryset, '_clone'):
                queryset = queryset._clone()
        elif self.model is not None:
            queryset = self.model._default_manager.all()
        else:
            raise ImproperlyConfigured("'%s' must define 'queryset' or 'model'"
                                       % self.__class__.__name__)
        return queryset

    def get_resource_name(self):
        return self.resource_name

    def get_content_type(self):
        return 'application/json'

    def create_get_context(self, request):
        pks = self.kwargs.get(self.pks_url_key, '')
        pks = pks.split(',') if pks else []
        nr_pks = len(pks)
        if nr_pks == 1:
            mode = 'get'
        else:
            mode = 'get_multiple'
        return RequestContext(request, pks, mode)

    def extract_resources(self, request):
        body = request.body
        if not body:
            raise MissingRequestBody()
        resource_name = self.get_resource_name()
        try:
            data = self.parse_json(body)
            if not resource_name in data:
                raise InvalidDataFormat('Missing %s as key' % resource_name)
            obj = data[resource_name]
            if isinstance(obj, list):
                resource = None
                resources = obj
                many = True
            else:
                resource = obj
                resources = [obj]
                many = False
            return resource, resources, many
        except ValueError:
            raise InvalidDataFormat()

    def parse_json(self, data):
        return json.loads(data)

    def create_json(self, data, *args, **kwargs):
        return json.dumps(data, *args, **kwargs)

    def get_methods(self):
        return self.methods


class JsonApiEndpoint(PostWithFormMixin, PutWithFormMixin, DeleteMixin, GetJsonApiEndpoint):
    pass
