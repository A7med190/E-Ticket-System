from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        custom_response = {
            'status_code': response.status_code,
            'error': response.data.get('detail', str(response.data)),
        }

        if isinstance(response.data, dict):
            if 'detail' not in response.data:
                custom_response['errors'] = response.data

        response.data = custom_response

    return response
