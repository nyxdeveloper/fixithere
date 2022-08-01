from rest_framework.exceptions import APIException


class InvalidField(APIException):
    default_detail = 'Невалидное поле'
    status_code = 400


class InvalidPassword(InvalidField):
    default_detail = 'Пароль должен быть не менее 8 символов в длинну, содержать прописные и заглавные ' \
                     'буквы латинского алфавита, а так же минимум один специальный символ'


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


class SelfAppointedOffer(APIException):
    status_code = 400
    default_detail = 'Невозможно назначить оффер самому себе'


class Forbidden(APIException):
    status_code = 403
    default_detail = 'Действие запрещено'


class MasterRoleRequired(APIException):
    status_code = 403
    default_detail = 'Для проведения данного действия переключите ваш аккаунт в статус мастера в профиле'


class BadRequest(APIException):
    status_code = 400
    default_detail = 'Невалидный запрос'
