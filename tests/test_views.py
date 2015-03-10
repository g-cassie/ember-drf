from django.test import TestCase

from rest_framework import status
from rest_framework.exceptions import ValidationError, APIException
from rest_framework.settings import api_settings
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from ember_drf.views import exception_handler

factory = APIRequestFactory()


class ValidationErrorView(APIView):
    def get(self, request, *args, **kwargs):
        raise ValidationError('invalid data')


class ErrorView(APIView):
    def get(self, request, *args, **kwargs):
        raise APIException('invalid data')


class ExceptionHandlerTests(TestCase):

    def setUp(self):
        api_settings.EXCEPTION_HANDLER = exception_handler

    def test_validation_error_handling(self):
        view = ValidationErrorView.as_view()

        request = factory.get('/', content_type='application/json')
        response = view(request)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data, {'errors': ['invalid data']})

    def test_error_handling(self):
        view = ErrorView.as_view()

        request = factory.get('/', content_type='application/json')
        response = view(request)
        self.assertEqual(response.status_code,
                         status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data, {'detail': 'invalid data'})
