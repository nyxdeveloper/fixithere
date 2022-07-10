import typing

from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.renderers import json

from django.contrib.auth import authenticate
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from dateutil.relativedelta import relativedelta

from .aggregations import annotate_comments_likes_count
from .aggregations import annotate_repair_offers_views_count
from .aggregations import annotate_repair_offers_my_my_accept_free
from .aggregations import annotate_repair_offers_completed

from .models import User
from .models import CarBrand
from .models import Car
from .models import RepairCategory
from .models import OfferImage
from .models import Grade
from .models import GradePhoto
from .models import Comment
from .models import CommentMedia
from .models import RepairOffer
from .models import Chat
from .models import Message
from .models import MessageMedia
from .models import SubscriptionPlan
from .models import Subscription

from .serializers import CarBrandSerializer
from .serializers import CarSerializer
from .serializers import UserProfileSerializer
from .serializers import RepairCategorySerializer
from .serializers import OfferImageSerializer
from .serializers import GradeSerializer
from .serializers import GradePhotoSerializer
from .serializers import CommentSerializer
from .serializers import CommentMediaSerializer
from .serializers import RepairOfferSerializer
from .serializers import SubscriptionPlanSerializer
from .serializers import ChatSerializer
from .serializers import MessageSerializer
from .serializers import MessageMediaSerializer

from .services import validate_registration_data
from .services import register_user
from .services import send_user_approve_email
from .services import send_password_recovery_approve
from .services import get_access_token
from .services import check_otc
from .services import get_user_by_email
from .services import recovery_password
from .services import query_params_filter
from .services import set_master
from .services import offers_base_filter
from .services import get_files_from_request
from .services import subscription_plans_base_filter
from .services import has_offer_chat

from .exceptions import AuthenticationFailed
from .exceptions import Forbidden
from .exceptions import BadRequest

from .paginations import StandardPagination

from yookassa import Configuration, Payment

Configuration.account_id = settings.YOOKASSA["account_id"]
Configuration.secret_key = settings.YOOKASSA["secret_key"]


# custom views
class CustomApiView(GenericAPIView):
    pass


class CustomReadOnlyModelViewSet(ReadOnlyModelViewSet):
    filterset_key_fields = list()
    filterset_char_fields = list()

    def filter_queryset(self, queryset):
        queryset = super(CustomReadOnlyModelViewSet, self).filter_queryset(queryset)
        queryset = query_params_filter(self.request, queryset, self.filterset_key_fields, self.filterset_char_fields)
        return queryset


class CustomModelViewSet(ModelViewSet):
    filterset_key_fields = list()
    filterset_char_fields = list()

    def filter_queryset(self, queryset):
        queryset = super(CustomModelViewSet, self).filter_queryset(queryset)
        queryset = query_params_filter(self.request, queryset, self.filterset_key_fields, self.filterset_char_fields)
        return queryset


# authorization
class EmailRegistration(CustomApiView):
    @transaction.atomic
    def post(self, request):
        email, password, name = request.data.get('email'), request.data.get('password'), request.data.get('name')
        validate_registration_data(email, password, name)
        register_user(email, password, name)
        send_user_approve_email(email)
        return Response({'detail': 'Для подтверждения регистрации перейдите по ссылке из письма'}, status=200)


class EmailAuthorization(CustomApiView):
    def post(self, request):
        email, password = request.data.get('email'), request.data.get('password')
        user = authenticate(username=email, password=password)
        if user.is_anonymous:
            raise AuthenticationFailed
        return Response({'token': get_access_token(user, request)})


class EmailApprove(CustomApiView):
    def get(self, request):
        code, email = request.query_params.get('c'), request.query_params.get('e')
        user = get_user_by_email(email)
        check_otc(email, code, delete=True, description='email_approve')
        user.approve_email = True
        user.save()
        return Response({'detail': 'Email успешно подтвержден'}, status=200)


class PasswordRecovery(CustomApiView):
    def get(self, request):
        code, email = request.query_parrams.get('c'), request.query_parrams.get('e')
        user = get_user_by_email(email)
        check_otc(email, code, delete=True, description='password_recovery')
        recovery_password(user)
        return Response({'detail': f'Новый пароль отправлен на почту {email}'}, status=200)

    def post(self, request):
        email = request.data.get('email')
        get_user_by_email(email)
        send_password_recovery_approve(email)
        return Response({'detail': 'Перейдите по ссылке из письма для подтверждения сброса пароля'}, status=200)


class ProfileAPIView(CustomApiView):
    serializer_class = UserProfileSerializer

    def get(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=200)

    def post(self, request):
        serializer = self.get_serializer(data=request.data, instance=request.user)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=200)


class ProfileCarsAPIView(CustomApiView):
    serializer_class = CarSerializer

    def get(self, request):
        serializer = self.get_serializer(request.user.cars.all(), many=True)
        return Response(serializer.data, status=200)

    @transaction.atomic
    def post(self, request):
        try:
            cars_id: typing.List[int] = request.data.get('cars')
        except TypeError:
            return Response({'detail': 'Невалидный список идентификаторов'})
        request.user.cars.clear()
        request.user.cars.add(*cars_id)
        return Response({'detail': 'Список машин успешно обновлен'}, status=200)


# repair offers
class CarBrandReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = CarBrand.objects.all()
    serializer_class = CarBrandSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['id', 'name']


class CarReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['brand__name', 'model_name']
    ordering_fields = ['id', 'brand__name', 'model_name']
    filterset_key_fields = ['brand']
    filterset_char_fields = ['brand__name', 'model_name']


class RepairCategoryReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = RepairCategory.objects.all()
    serializer_class = RepairCategorySerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['id', 'name']


class OfferImageReadOnlyViewSet(CustomModelViewSet):
    queryset = OfferImage.objects.all()
    serializer_class = OfferImageSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['id']
    filterset_key_fields = ['offer']

    def is_master(self, instance):
        return instance.offer.master_id == self.request.user.id

    def is_owner(self, instance):
        return instance.offer.owner_id == self.request.user.id

    def perform_destroy(self, instance):
        if not self.is_owner(instance):
            raise Forbidden('Вы не можете удалить картинку чужого оффера')
        return super(OfferImageReadOnlyViewSet, self).perform_destroy(instance)

    def perform_update(self, serializer):
        if not self.is_owner(self.get_object()):
            raise Forbidden('Вы не можете изменить картинку чужого оффера')
        return super(OfferImageReadOnlyViewSet, self).perform_update(serializer)

    @transaction.atomic()
    def perform_create(self, serializer):
        serializer.save()
        if not self.is_owner(serializer.instance):
            raise Forbidden('Вы не можете добавить картинку в чужой оффер')


class GradeReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['comment']
    ordering_fields = ['grade', 'created']
    filterset_key_fields = ['rating_user', 'valued_user']


class GradePhotoReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = GradePhoto.objects.all()
    serializer_class = GradePhotoSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['id']
    filterset_key_fields = ['grade']


class CommentReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    ordering_fields = ['created', 'users_liked_count']
    search_fields = ['text']
    filterset_key_fields = ['offer', 'reply', 'user']

    def get_queryset(self):
        queryset = self.queryset
        queryset = annotate_comments_likes_count(queryset)  # annotate 'users_liked_count' variable
        return queryset


class CommentMediaReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = CommentMedia.objects.all()
    serializer_class = CommentMediaSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['id']
    filterset_key_fields = ['comment']


class RepairOfferViewSet(CustomModelViewSet):
    queryset = RepairOffer.objects.all()
    serializer_class = RepairOfferSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title', 'description', 'categories__name']
    ordering_fields = ['created', 'private', 'views_count']
    filterset_key_fields = ['owner', 'master', 'categories', 'private', 'my', 'my_accept', 'free', 'completed']
    filterset_char_fields = ['title']

    def is_master(self, instance):
        return instance.master_id == self.request.user.id

    def is_owner(self, instance):
        return instance.owner_id == self.request.user.id

    def get_queryset(self):
        queryset = offers_base_filter(self.queryset, self.request.user.id)
        user_id = self.request.user.id  # current user id
        queryset = annotate_repair_offers_views_count(queryset)  # annotate 'views_count' variable
        queryset = annotate_repair_offers_my_my_accept_free(queryset,
                                                            user_id)  # annotate 'my', 'my_accept' and 'free' boolean variable
        queryset = annotate_repair_offers_completed(queryset)  # annotate 'completed' boolean variable
        return queryset

    def perform_destroy(self, instance):
        if not self.is_owner(instance):
            raise Forbidden('Вы не можете удалить чужой оффер')
        return super(RepairOfferViewSet, self).perform_destroy(instance)

    def perform_update(self, serializer):
        if not self.is_owner(self.get_object()):
            raise Forbidden
        return super(RepairOfferViewSet, self).perform_update(serializer)

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save()
        offer = serializer.instance
        try:
            images: typing.List[InMemoryUploadedFile] = self.request.data.get('images')
            for img in images:
                offer.images.create(img=img)
        except TypeError:
            raise BadRequest(detail='Список картинок должен представлять собой массив бинарных файлов')

    @action(methods=['post'], detail=True)
    def set_master(self, request, pk):
        instance = self.get_object()
        if not self.is_owner(instance):
            raise Forbidden
        set_master(instance, request.data.get('master_id'))
        return Response({'detail': 'Мастер успешно изменен'}, status=200)

    @transaction.atomic
    @action(methods=['post'], detail=True)
    def send_grade(self, request, pk):
        instance = self.get_object()
        try:
            grade_value: int = int(request.data.get('grade'))
            comment: str = str(request.data.get('comment'))
            if grade_value > 5 or grade_value < 1:
                raise ValueError
        except (TypeError, ValueError) as e:
            raise BadRequest('Оценка должна быть целым числом от 1 до 5, а комментарий строкой')

        if self.is_owner(instance):
            if instance.owner_grade:
                raise BadRequest('Нельзя оставлять более одного отзыва на оффер')
            grade = Grade.objects.create(
                grade=grade_value, comment=comment, rating_user=instance.owner, valued_user=instance.master
            )
            instance.owner_grade = grade
            instance.save()
        elif self.is_master(instance):
            if instance.master_grade:
                raise BadRequest('Нельзя оставлять более одного отзыва на оффер')
            grade = Grade.objects.create(
                grade=grade_value, comment=comment, rating_user=instance.master, valued_user=instance.owner
            )
            instance.master_grade = grade
            instance.save()
        else:
            raise Forbidden('Отзыв можно оставлять только своим офферам')

        for photo in get_files_from_request(request, 'photo'):
            grade.images.create(img=photo)

        return Response({'detail': 'Отзыв отправлен'}, status=200)

    @transaction.atomic
    @action(methods=['post'], detail=True)
    def respond(self, request, pk):
        instance = self.get_object()
        offer_id = str(instance.pk)
        if request.user.role != 'master':
            raise Forbidden('Для проведения данного действия переключите ваш аккаунт в статус мастера в профиле')
        if request.user.id == instance.owner_id:
            raise BadRequest('Нельзя откликаться на свои же офферы')
        Subscription.check_action(request.user, 'can_take_offers')
        if has_offer_chat(instance, request.user):
            raise BadRequest('По данному офферу у вас уже создан чат')

        chat = Chat(object_id=offer_id, object_type='repair_offer', created_user=request.user, private=True)
        chat.save()
        chat.participants.add(request.user.id, instance.owner_id)
        text = request.data.get('text')
        if not text:
            text = '👋'
        chat.message_set.create(user=request.user, text=text)
        return Response({'detail': 'Чат успешно создан'}, status=200)

    @transaction.atomic
    @action(methods=['post'], detail=True)
    def suggest(self, request, pk):
        instance = self.get_object()
        offer_id = str(instance.pk)
        master_id = request.data.get('master_id')
        if instance.master:
            raise BadRequest('На данный оффер уже назначен мастер. Снимите его чтобы предложить оффер другому мастеру')
        if not master_id:
            raise BadRequest('Выберите мастера')
        if not User.objects.filter(role='master', id=master_id, is_active=True).exists():
            raise BadRequest('лидный идентификатор мастера')
        if request.user.id != instance.owner_id:
            raise BadRequest('Можно предлагать мастерам только свои офферы')
        if has_offer_chat(instance, request.user):
            raise BadRequest('По данному офферу у вас уже создан чат с этим мастером')

        chat = Chat(object_id=offer_id, object_type='repair_offer', created_user=request.user, private=True)
        chat.save()
        chat.participants.add(request.user.id, instance.owner_id)
        text = request.data.get('text')
        if not text:
            text = '👋'
        chat.message_set.create(user=request.user, text=text)
        return Response({'detail': 'Чат успешно создан'}, status=200)


class SubscriptionViewSet(CustomReadOnlyModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAuthenticated]
    actions_permission_classes = {
        'default': [AllowAny],
        'active': [IsAuthenticated],
        'pay': [IsAuthenticated],
    }

    def get_queryset(self):
        queryset = subscription_plans_base_filter(self.queryset)
        return queryset

    def get_permissions(self):
        if self.action in self.actions_permission_classes:
            return [permission() for permission in self.actions_permission_classes[self.action]]
        return [permission() for permission in self.actions_permission_classes['default']]

    @action(methods=['get'], detail=False)
    def active(self, request):
        sub = Subscription.get_active(request.user)
        if sub:
            plan = sub.plan
        else:
            plan = self.get_queryset().get(default=True)
        serializer = self.get_serializer(plan)
        return Response({
            'plan': serializer.data,
            'expirate': sub.expiration_date.strftime("%d.%m.%Y") if sub else None
        })

    @transaction.atomic
    @action(methods=['post'], detail=True)
    def pay(self, request, pk):
        plan = self.get_object()
        if plan.disabled:
            return Response({"detail": "Данный тариф заблокирован"}, status=400)

        payment_data = {
            "amount": {
                "value": str(plan.cost),
                "currency": str(plan.currency)
            },
            "confirmation": {
                "type": "redirect",
                "return_url": settings.YOOKASSA["confirmation_redirect_url"]
            },
            "capture": True,
            "description": "Подписка по тарифному плану \"" + plan.name + "\", пользователь " + request.user.name
        }
        try:
            payment = Payment.create(payment_data)
        except Exception as e:
            return Response({"detail": e.__str__()}, status=400)

        value = payment_data['amount']['value'] + payment_data["amount"]["currency"]
        sub = Subscription.get_active(request.user)
        if sub:
            start = sub.expiration_date
        else:
            start = timezone.now().date()
        if plan.duration_type == 'yer':
            expiration_date = start + relativedelta(years=plan.duration)
        elif plan.duration_type == 'mon':
            expiration_date = start + relativedelta(months=plan.duration)
        else:
            expiration_date = start + relativedelta(days=plan.duration)
        if not Subscription.objects.filter(payment_id=payment.id).exists():
            Subscription.objects.create(
                payment_id=payment.id,
                value=value,
                start=start,
                expiration_date=expiration_date,
                user=request.user,
                plan=plan
            )
        return Response(json.loads(payment.json()))

    @action(methods=['post'], detail=False)
    def pay_notifications(self, request):
        payment = request.data.get("object")
        if payment["status"] == "succeeded":
            Subscription.objects.filter(payment_id=payment["id"]).update(active=True)
        else:
            Subscription.objects.filter(payment_id=payment["id"]).delete()
        return Response(status=200)


class ChatReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = Chat.objects.filter(deleted=False)
    serializer_class = ChatSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'participants__name', 'participants__email']
    ordering_fields = ['created', 'changed', 'private']
    filterset_key_fields = ['object_id', 'object_type', 'private', 'created_user']
    filterset_char_fields = ['name']

    def get_queryset(self):
        return self.queryset.filter(participants=self.request.user)


class MessageReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = Message.objects.filter(deleted=False)
    serializer_class = MessageSerializer
    pagination_class = StandardPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['text']
    ordering_fields = ['created', 'changed']
    filterset_key_fields = ['chat', 'user', 'reply', 'have_read']

    def get_queryset(self):
        return self.queryset.filter(chat__participants=self.request.user)
