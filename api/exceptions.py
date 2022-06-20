from rest_framework.exceptions import APIException


class InvalidField(APIException):
    default_detail = 'Невалидное поле'
    status_code = 400


class InvalidPassword(InvalidField):
    default_detail = 'Пароль должен содержать прописные и заглавные буквы латинского алфавита, а так же минимум один специальный символ'


class InvalidEmail(InvalidField):
    default_detail = 'Введите корректный Email'


class InvalidName(InvalidField):
    default_detail = 'Введите корректное имя'


class AuthenticationFailed(APIException):
    status_code = 400
    default_detail = 'Неверный логин или пароль'


class InvalidOTC(APIException):
    status_code = 400
    default_detail = 'Невалидный одноразовый код'


class UserDoesNotExist(APIException):
    status_code = 404
    default_detail = 'Пользователь не найден'
