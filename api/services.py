import re
import random
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import user_logged_in
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from .exceptions import InvalidEmail
from .exceptions import InvalidPassword
from .exceptions import InvalidName
from .exceptions import InvalidOTC
from .exceptions import UserDoesNotExist
from .exceptions import BadRequest
from .models import User, OTC
from django.db.models import Q
from django.contrib.postgres.search import SearchVector
from django.contrib.postgres.search import SearchQuery

from .models import Chat


def get_user_by_email(email):
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        raise UserDoesNotExist


def get_user_by_token(token: str):
    access_token_obj = AccessToken(token)
    user_id = access_token_obj['user_id']
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        user = AnonymousUser()
    return user


def generate_code(l: int, num: bool = False):
    if num:
        choices = '1234567890'
    else:
        choices = 'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM1234567890#$%'
    return ''.join([random.choice(choices) for _ in range(l)])


def generate_otc(key: str, l: int, num: bool = False, description: str = ''):
    if settings.DEBUG:
        code = '1111'
    else:
        code = generate_code(l, num)
    OTC.objects.create(key=key, code=code, description=description)
    return code


def check_otc(key: str, code: str, delete: bool = False, description: str = None):
    kwargs = {'key': key, 'code': code}
    if description:
        kwargs['description'] = description
    try:
        otc = OTC.objects.get(**kwargs)
        if delete:
            otc.delete()
    except OTC.DoesNotExist:
        raise InvalidOTC


def validate_email(email: str):
    regex = r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+'
    return re.fullmatch(regex, email)


def validate_name(name: str):
    return len(name.replace(' ', '')) >= 2


def validate_password(password: str):
    if len(password) < 8:
        return False
    elif password.replace(' ', '') == '':
        return False
    elif password.lower() == password:
        return False
    elif password.upper() == password:
        return False
    elif True not in [i in password for i in '!@#$%^&?*()№.":-_=+\'{[}]\\|/,<>;']:
        return False
    return True


def validate_registration_data(email: str, password: str, name: str):
    if not email:
        raise InvalidEmail('Введите Email')
    elif not validate_email(email):
        raise InvalidEmail
    elif User.objects.filter(email=email).exists():
        raise InvalidEmail('Пользователь с таким Email уже зарегистрирован в системе')
    elif not password:
        raise InvalidPassword('Введите пароль')
    elif not validate_password(password):
        raise InvalidPassword
    elif not name:
        raise InvalidName('Введите имя')
    elif not validate_name(name):
        raise InvalidName('Введите корректное имя')
    return True


def register_user(email: str, password: str, name: str):
    user = User()
    user.email = email
    user.name = name
    user.set_password(password)
    user.save()
    return user


def send_password_recovery_approve(email):
    url_root = settings.APPROVE_PASSWORD_RECOVERY_URL
    params = f'?c={generate_otc(email, 30, description="password_recovery")}&e={email}'
    href = url_root + params
    subject = 'FIXITHERE подтверждение сброса пароля'
    body = f'Перейдите по ссылке чтобы подтвердить сброс пароля:\n{href}\n' \
           f'Если вы получили это письмо по ошибке, удалите его!'
    send_mail(subject, body, settings.EMAIL_HOST_USER, [email], fail_silently=False)


def recovery_password(user):
    new_password = generate_code(8, False)
    user.set_password(new_password)
    user.save()
    subject = 'FIXITHERE новый пароль'
    body = f'Здравствуйте, {user.nam}!\n' \
           f'Ваш логин: {user.get_username()}' \
           f'Ваш новый пароль: {new_password}\n' \
           f'Если вы получили это письмо по ошибке, удалите его!'
    send_mail(subject, body, settings.EMAIL_HOST_USER, [user.email], fail_silently=False)


def send_user_approve_email(email):
    url_root = settings.APPROVE_EMAIL_URL
    params = f'?c={generate_otc(email, 30, description="email_approve")}&e={email}'
    if settings.DEBUG:
        return None
    href = url_root + params
    subject = 'FIXITHERE подтверждение почты'
    body = f'Перейдите по ссылке чтобы подтвердить свой аккаунт:\n{href}\n' \
           f'Если вы получили это письмо по ошибке, удалите его!'
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False
    )


def get_access_token(user, request):
    token = str(RefreshToken.for_user(user).access_token)
    user_logged_in.send(sender=user.__class__, request=request, user=user)
    return token


def query_params_filter(request, queryset, key_fields, char_fields):
    if len(request.query_params):
        for p in request.query_params:
            if p in key_fields:
                queryset = queryset.filter(**{'%s__in' % p: request.query_params.getlist(p)})
            elif p in char_fields:
                queryset = queryset.filter(**{'%s__icontains' % p: request.query_params.get(p)})
            elif p.replace("ex_", "") in key_fields:
                queryset = queryset.exclude(**{'%s__in' % p: request.query_params.getlist(p)})
            elif p.replace("ex_", "") in char_fields:
                queryset = queryset.exclude(**{'%s__icontains' % p: request.query_params.get(p)})
    return queryset


def exclude_words(request, queryset, fields):
    exclude_string = request.query_params.get('exclude_words')
    if exclude_string:
        words = exclude_string.split(',')
        vector = SearchVector(*fields)
        # query = SearchQuery(words)
        # queryset = queryset.annotate(exclude_words=vector).exclude(exclude_words=query)
        queryset = queryset.annotate(exclude_words=vector)
        for w in words:
            queryset = queryset.exclude(exclude_words=w)
    return queryset


def set_master(instance, master_id):
    if master_id is None:
        instance.master = None
        instance.save()
    elif User.objects.filter(role='master', id=master_id).exists():
        instance.master_id = master_id
        instance.save()
    else:
        raise UserDoesNotExist('Мастер не найден')


def offers_base_filter(queryset, user_id):
    return queryset.filter(
        Q(private=False) |
        Q(owner_id=user_id, private=True) |
        Q(master_id=user_id, private=True)
    )


def subscription_plans_base_filter(queryset):
    now_date = timezone.now().date()
    return queryset.filter(
        Q(active_date_start__lte=now_date, active_date_end__isnull=True) |
        Q(active_date_end__gte=now_date, active_date_start__isnull=True) |
        Q(active_date_start__lte=now_date, active_date_end__gte=now_date) |
        Q(active_date_end__isnull=True, active_date_start__isnull=True)
    )


def has_offer_chat(repair_offer, user):
    return Chat.objects.filter(object_id=repair_offer.id, object_type='repair_offer', participants=user).exists()
