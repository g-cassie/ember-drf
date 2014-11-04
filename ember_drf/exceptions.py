from rest_framework.exceptions import ValidationError

class ActiveModelValidationError(ValidationError):
    """
    Override default ValidationError to return HTTP 422 repsonse.

    See http://emberjs.com/api/data/classes/DS.ActiveModelAdapter.html#method_ajaxError
    """
    status_code = 422
