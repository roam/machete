# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, print_function, division,
                        absolute_import)

import json
from contextlib import contextmanager

from django.db import transaction
from django.views.generic import View
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404

from .serializers import serialize
from .exceptions import (JsonApiError, MissingRequestBody, InvalidDataFormat,
                         IdMismatch, FormValidationError)
from .utils import RequestContext, RequestWithResourceContext, pluck_ids


@contextmanager
def not_atomic(using=None):
    yield


class GetEndpoint(View):
    """
    Extends a generic View to provide support for retrieving resources.

    Some methods might seem convoluted, but they're mostly built that
    way to provide useful points of extension/override. Methods are
    rarely passed all information, but request-method methods
    (get, post,...) should provide a context object containing the
    necessary information under ``self.context``.

    """

    content_type = 'application/json'  # Default to this for now; works better in browsers
    methods = ['get']
    pks_url_key = 'pks'
    pk_field = 'pk'
    queryset = None
    form_class = None

    def __init__(self, *args, **kwargs):
        super(GetEndpoint, self).__init__(*args, **kwargs)
        self.context = None
        # Django uses http_method_names to know which methods are
        # supported, we always add options on top which will advertise
        # the actual methods we support.
        self.http_method_names = self.get_methods() + ['options']

    def dispatch(self, request, *args, **kwargs):
        # Override dispatch to enable the handling or errors we can
        # handle.
        self.relationship = kwargs.get('relationship')
        manager, m_args, m_kwargs = self.context_manager()
        try:
            with manager(*m_args, **m_kwargs):
                return super(GetEndpoint, self).dispatch(request, *args, **kwargs)
        except Exception as error:
            return self.handle_error(error)

    def options(self, request, *args, **kwargs):
        # From the JSON API FAQ:
        # http://jsonapi.org/faq/#how-to-discover-resource-possible-actions
        self.context = self.create_get_context(request)
        actions = self.possible_actions()
        return HttpResponse(','.join(a.upper() for a in actions))

    def possible_actions(self):
        """
        Returns a list of allowed methods for this endpoint.

        You can use the context (a GET context) to determine what's
        possible. By default this simply returns all allowed methods.

        """
        return self.get_methods()

    def get(self, request, *args, **kwargs):
        self.context = self.create_get_context(request)
        collection = False
        if self.relationship:
            if self.context.relationship_pk:
                data = self.get_linked_resource()
            else:
                data = self.get_linked_resources()
                collection = True
        else:
            if self.context.pk:
                data = self.get_resource()
            else:
                data = self.get_resources()
                collection = True
        return self.create_http_response(data, collection=collection)

    def create_http_response(self, data, collection=False):
        """
        Creates a HTTP response from the data.

        The data might be an (a) HttpResponse object, (b) dict or (c)
        object that can be serialized.

        HttpResponse objects will simply be returned without further
        processing, dicts will be turned into JSON and returned as a
        response using the status attribute of the context. Other
        objects will be serialized using ``serialize`` method.

        """
        if isinstance(data, HttpResponse):
            # No more processing necessary
            return data
        if isinstance(data, dict):
            # How nice. Use it!
            response_data = data
        else:
            # Everything else: run it through the serialization process
            response_data = self.serialize(data, collection=collection)
        json_data = self.create_json(response_data, indent=2)
        status = self.context.status
        content_type = self.get_content_type()
        response = HttpResponse(json_data, content_type=content_type, status=status)
        return self.postprocess_response(response, data, response_data, collection)

    def serialize(self, data, collection=False, compound=False):
        """
        Serializes the data.

        Note that a serializer must have been registered with the name
        of this resource.

        """
        context = self.context.__dict__
        return serialize(self.get_resource_name(), data, many=collection, compound=True, context=context)

    def handle_error(self, error):
        # TODO Improve error reporting
        error_object = {}
        if isinstance(error, FormValidationError):
            error_object['message'] = '%s' % error
            return HttpResponse(self.create_json({'errors': error_object}), status=400)
        if isinstance(error, Http404):
            error_object['message'] = '%s' % error
            return HttpResponse(self.create_json({'errors': error_object}), status=404)
        if isinstance(error, JsonApiError):
            error_object['message'] = '%s' % error
            return HttpResponse(self.create_json({'errors': error_object}), status=500)
        raise error

    def postprocess_response(self, response, data, response_data, collection):
        """
        If you need to do any further processing of the HttpResponse
        objects, this is the place to do it.

        """
        return response

    def get_resource(self):
        """
        Grabs the resource for a resource request.

        Maps to ``GET /posts/1``.

        """
        filter = {self.get_pk_field(): self.context.pk}
        return self.get_queryset().get(**filter)

    def get_resources(self):
        """
        Grabs the resources for a collection request.

        Maps to ``GET /posts/1,2,3`` or ``GET /posts``.

        """
        qs = self.get_queryset()
        if self.context.pks:
            filter = {'%s__in' % self.get_pk_field(): self.context.pks}
            qs = qs.filter(**filter)
        return qs

    def get_linked_resources(self):
        resource = self.get_resource()
        return getattr(resource, self.relationship)

    def is_changed_besides(self, resource, model):
        # TODO Perform simple diff of serialized model with resource
        return False

    def get_pk_field(self):
        """
        Determines the name of the primary key field of the model.

        Either set the ``pk_field`` on the class or override this method
        when your model's primary key points to another field than the
        default.

        """
        return self.pk_field

    def get_queryset(self):
        """
        Get the list of items for this endpoint.

        This must be an iterable, and may be a queryset
        (in which qs-specific behavior will be enabled).
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
        """
        Determines the name of this resource.

        Override this method or set ``resource_name`` on the class.

        """
        return self.resource_name

    def get_content_type(self):
        """
        Determines the content type of responses.

        Override this method or set ``content_type`` on the class.

        """
        return self.content_type

    def create_get_context(self, request):
        """Creates the context for a GET request."""
        pks = self.kwargs.get(self.pks_url_key, '')
        pks = pks.split(',') if pks else []
        nr_pks = len(pks)
        if nr_pks == 1:
            mode = 'get'
        else:
            mode = 'get_multiple'
        return RequestContext(request, pks, mode)

    def extract_resources(self, request):
        """
        Extracts resources from the request body.

        This should probably be moved elsewhere since it doesn't make
        sense in a GET request. But still.

        """
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

    def context_manager(self):
        if self.request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            return (transaction.atomic, [], {})
        return (not_atomic, [], {})


class WithFormMixin(object):
    """
    Mixin supporting create and update of resources with a model form.

    Note that it relies on some methods made available by the
    GetEndpoint.

    """

    form_class = None

    def get_form_kwargs(self, **kwargs):
        return kwargs

    def get_form_class(self):
        return self.form_class

    def get_form(self, resource, instance=None):
        """Constructs a new form instance with the supplied data."""
        data = self.prepare_form_data(resource, instance)
        form_kwargs = {'data': data, 'instance': instance}
        form_kwargs = self.get_form_kwargs(**form_kwargs)
        form_class = self.get_form_class()
        if not form_class:
            raise ImproperlyConfigured('Missing form_class')
        return form_class(**form_kwargs)

    def prepare_form_data(self, resource, instance=None):
        """Last chance to tweak the data being passed to the form."""
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
    """
    Provides support for POST requests on resources.

    Since a successful response must include a location header, you
    should set ``url_name`` or ``url_name_detail``, or override the
    ``create_resource_url`` method.

    The ``create_resource`` method must be implemented to actually do
    something.

    """

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
        """Create the resource and return the corresponding model."""
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
    """
    Provides an implementation of ``create_resource`` using a form.

    """

    def create_resource(self, resource):
        form = self.get_form(resource)
        if form.is_valid():
            return form.save()
        raise FormValidationError('', form=form)


class PutMixin(object):
    """
    Provides support for PUT requests on resources.

    This supports both full and partial updates, on single and multiple
    resources.

    Requires ``update_resource`` to be implemented.

    """

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
    """
    Provides an implementation of ``update_resource`` using a form.

    """

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
    """
    Provides support for DELETE request on single + multiple resources.

    """

    def get_methods(self):
        return super(DeleteMixin, self).get_methods() + ['delete']

    def delete(self, request, *args, **kwargs):
        self.context = self.create_delete_context(request)
        if not self.context.pks:
            raise Http404('Missing ids')
        # Although the default implementation defers DELETE request for
        # both single and multiple resources to the ``perform_delete``
        # method, we still split based on
        if self.context.pk:
            not_deleted = self.delete_resource()
        else:
            not_deleted = self.delete_resources()
        if not_deleted:
            raise Http404('Resources %s not found' % ','.join(not_deleted))
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


class Endpoint(PostWithFormMixin, PutWithFormMixin, DeleteMixin, GetEndpoint):
    """
    Ties everything together.

    Use this base class when you need to support GET, POST, PUT and
    DELETE and want to use a form to process incoming data.

    """

    pass
