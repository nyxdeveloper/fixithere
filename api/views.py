from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter

from django.contrib.auth import authenticate

from .aggregations import annotate_comments_likes_count
from .aggregations import annotate_repair_offers_views_count

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

from .exceptions import AuthenticationFailed


class CustomApiView(APIView):
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


class EmailRegistration(CustomApiView):
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
        code, email = request.query_parrams.get('c'), request.query_parrams.get('e')
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


class CarBrandReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = CarBrand.objects.all()
    serializer_class = CarBrandSerializer
    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['id', 'name']


class CarReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['brand__name', 'model_name']
    ordering_fields = ['id', 'brand__name', 'model_name']
    filterset_key_fields = ['brand']
    filterset_char_fields = ['brand__name', 'model_name']


class RepairCategoryReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = RepairCategory.objects.all()
    serializer_class = RepairCategorySerializer
    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['id', 'name']


class OfferImageReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = OfferImage.objects.all()
    serializer_class = OfferImageSerializer
    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['id']
    filterset_key_fields = ['offer']


class GradeReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer
    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['comment']
    ordering_fields = ['grade', 'created']
    filterset_key_fields = ['rating_user', 'valued_user']


class GradePhotoReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = GradePhoto.objects.all()
    serializer_class = GradePhotoSerializer
    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['id']
    filterset_key_fields = ['grade']


class CommentReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    pagination_class = PageNumberPagination
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
    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['id']
    filterset_key_fields = ['comment']


class RepairOfferReadOnlyViewSet(CustomReadOnlyModelViewSet):
    queryset = RepairOffer.objects.all()
    serializer_class = RepairOfferSerializer
    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title', 'description', 'categories__name']
    ordering_fields = ['created', 'private', 'views_count']
    filterset_key_fields = ['owner', 'master', 'categories', 'private']
    filterset_char_fields = ['title']

    def get_queryset(self):
        queryset = self.queryset
        queryset = annotate_repair_offers_views_count(queryset)  # annotate 'views_count' variable
        return queryset
