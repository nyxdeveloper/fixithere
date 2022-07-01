from rest_framework.exceptions import AuthenticationFailed
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, AuthenticationFailed):
        custom_response_data = {"detail": "Ошибка авторизации."}
        response.data = custom_response_data
        response.status_code = 401

    return response
