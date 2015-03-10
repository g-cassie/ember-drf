from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from . import compat


def exception_handler(exc, context=None):
    """
    Returns the response that should be used for any given exception.

    By default we handle the REST framework `APIException`, and also
    Django's built-in `ValidationError`, `Http404` and `PermissionDenied`
    exceptions.

    Any unhandled exceptions may return `None`, which will cause a 500 error
    to be raised.
    """
    if isinstance(exc, ValidationError):
        data = {'errors': exc.detail}
        return Response(data, status=422)
    else:
        return compat.get_exception_handler(exc, context)
