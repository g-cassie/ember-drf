"""
This module provides support for backwards compatibility with older
versions of django-rest-framework.
"""
import inspect


def get_request_query_params(request):
    """
    `request.QUERY_PARAMS` has been deprecated in favor of `request.query_params`
    since version 3.0, and has been fully removed as of version 3.2.
    """
    try:
        return request.QUERY_PARAMS
    except NotImplementedError:
        return request.query_params


def get_related_model(relation_info):
    """
    `RelationInfo.related_model` was called `RelationInfo.related` prior to
    DRF 3.1.
    """
    try:
        return relation_info.related_model
    except AttributeError:
        return relation_info.related


def get_exception_handler(exc, context=None):
    """
    `exception_handler` did not accept context as an argument prior to DRF 3.1.
    """
    from rest_framework.views import exception_handler
    if len(inspect.getargspec(exception_handler)[0]) == 2:
        return exception_handler(exc, context)
    else:
        return exception_handler(exc)
