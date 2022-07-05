import typing

from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter

from django.contrib.auth import authenticate
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction

from .aggregations import annotate_comments_likes_count
from .aggregations import annotate_repair_offers_views_count
from .aggregations import annotate_repair_offers_my_my_accept_free

from .models import CarBrand
from .models import Car
from .models import RepairCategory
from .models import OfferImage
from .models import Grade
from .models import GradePhoto
from .models import Comment
from .models import CommentMedia
from .models import RepairOffer

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

from .exceptions import AuthenticationFailed
from .exceptions import Forbidden
from .exceptions import BadRequest

from .paginations import StandardPagination


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
    filterset_key_fields = ['owner', 'master', 'categories', 'private', 'my', 'my_accept', 'free']
    filterset_char_fields = ['title']

    def is_master(self, instance):
        return instance.master_id == self.request.user.id

    def is_owner(self, instance):
        return instance.owner_id == self.request.user.id

    def get_queryset(self):
        queryset = self.queryset
        user_id = self.request.user.id  # current user id
        queryset = annotate_repair_offers_views_count(queryset)  # annotate 'views_count' variable
        queryset = annotate_repair_offers_my_my_accept_free(queryset,
                                                            user_id)  # annotate 'my', 'my_accept' and 'free' boolean variable
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
        return Response({'detail': 'Мастер именен'}, status=200)
