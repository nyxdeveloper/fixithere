from rest_framework import serializers

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
from .models import SubscriptionAction
from .models import SubscriptionAction


class CarBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarBrand
        fields = '__all__'


class CarSerializer(serializers.ModelSerializer):
    _brand = CarBrandSerializer(read_only=True, source='brand')

    class Meta:
        model = Car
        fields = '__all__'


class UserProfileSerializer(serializers.ModelSerializer):
    cars = serializers.PrimaryKeyRelatedField(write_only=True, queryset=Car.objects.all(), many=True)
    _cars = CarSerializer(many=True, read_only=True, source='cars')

    class Meta:
        model = User
        fields = [
            'id', 'email', 'name', 'role', 'phone', 'whatsapp', 'telegram', 'vk', 'instagram', 'site', 'cars', '_cars',
            'avatar'
        ]


class RepairCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairCategory
        fields = '__all__'


class OfferImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferImage
        fields = '__all__'


class GradeSerializer(serializers.ModelSerializer):
    _rating_user = UserProfileSerializer(read_only=True, source='rating_user')
    _valued_user = UserProfileSerializer(read_only=True, source='valued_user')
    photo_count = serializers.SerializerMethodField()

    def get_photo_count(self, instance):
        return instance.images.count()

    class Meta:
        model = Grade
        fields = '__all__'


class GradePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradePhoto
        fields = '__all__'


class CommentSerializer(serializers.ModelSerializer):
    _user = UserProfileSerializer(read_only=True, source='user')
    users_liked = serializers.SerializerMethodField()
    reply_str = serializers.SerializerMethodField()
    cut_text = serializers.CharField(read_only=True)

    def get_users_liked(self, instance):
        if hasattr(instance, 'users_liked_count'):
            return instance.users_liked_count
        return instance.users_liked.count()

    def get_reply_str(self, instance):
        return instance.reply_str()

    class Meta:
        model = Comment
        fields = '__all__'


class CommentMediaSerializer(serializers.ModelSerializer):
    extension = serializers.CharField(read_only=True)
    filename = serializers.CharField(read_only=True)

    class Meta:
        model = CommentMedia
        fields = '__all__'


class RepairOfferSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    _owner = UserProfileSerializer(read_only=True, source='owner')
    _master = UserProfileSerializer(read_only=True, source='master')
    categories = serializers.PrimaryKeyRelatedField(many=True, queryset=RepairCategory.objects.all(), write_only=True)
    _categories = RepairCategorySerializer(read_only=True, many=True, source='categories')
    owner_grade = GradeSerializer(read_only=True)
    master_grade = GradeSerializer(read_only=True)
    views = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    images = OfferImageSerializer(read_only=True, many=True)

    # def get_images(self, instance):
    #     return [
    #         f"{self.context['request'].META['wsgi.url_scheme']}://{self.context['request'].META['HTTP_HOST']}{i.img.url}"
    #         for i in instance.images.all()
    #     ]

    def get_views(self, instance):
        return instance.views.count()

    def get_comments(self, instance):
        return instance.comments.count()

    class Meta:
        model = RepairOffer
        fields = '__all__'


class ChatSerializer(serializers.ModelSerializer):
    _name = serializers.SerializerMethodField(method_name='get_name')
    participants = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), write_only=True)
    deleted = serializers.HiddenField(default=False)
    unread_count = serializers.IntegerField(read_only=True)

    def get_name(self, instance):
        if instance.name:
            return instance.name
        else:
            if len(self.context):
                names = instance.participants.exclude(id=self.context['user'].id).values_list('name', flat=True)
            else:
                names = instance.participants.values_list('name', flat=True)
            return ', '.join(names)

    class Meta:
        model = Chat
        fields = [
            'id', 'name', '_name', 'object_id', 'object_type', 'created_user', 'participants', 'private', 'created',
            'changed'
        ]


class MessageSerializer(serializers.ModelSerializer):
    _user = UserProfileSerializer(read_only=True, source='user')
    read = serializers.SerializerMethodField()
    reply_str = serializers.SerializerMethodField()

    def get_read(self, instance):
        if len(self.context):
            return instance.have_read.exclude(id=self.context['user'].id).count() > 0
        return False

    def get_reply_str(self, instance):
        return instance.reply_str()

    class Meta:
        model = Message
        fields = ['id', 'user', '_user', 'reply', 'reply_str', 'read', 'chat', 'text', 'created', 'changed']


class MessageMediaSerializer(serializers.ModelSerializer):
    extension = serializers.CharField(read_only=True)
    filename = serializers.CharField(read_only=True)

    class Meta:
        model = MessageMedia
        fields = '__all__'


class SubscriptionActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionAction
        fields = ['name', 'value', ]


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    actions = SubscriptionActionSerializer(read_only=True, many=True)

    class Meta:
        model = SubscriptionPlan
        fields = '__all__'


class SubscriptionSerializer(serializers.Serializer):
    start = serializers.DateField(format="%d.%m.%Y", read_only=True)
    expiration_date = serializers.DateField(format="%d.%m.%Y", read_only=True)
    plan = serializers.CharField(read_only=True)
    value = serializers.CharField(read_only=True)
    active = serializers.BooleanField(read_only=True)
