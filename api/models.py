from django.db import models
from django.contrib.auth.models import PermissionsMixin, AbstractBaseUser, BaseUserManager
from django.core.validators import MaxValueValidator
from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.utils import timezone

from .exceptions import BadRequest
from .exceptions import Forbidden

from .signals import file_model_delete
from .signals import img_model_delete
from .signals import user_avatar_delete
from .signals import create_helpdesk_chat

from .exceptions import SelfAppointedOffer

import os


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password):
        user = self.model(email=email, password=password)
        user.set_password(password)
        user.is_staff = False
        user.is_superuser = False
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        user = self.create_user(email=email, password=password)
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, email_):
        return self.get(email=email_)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name='Email')
    is_active = models.BooleanField(default=True, verbose_name='Активный')
    is_staff = models.BooleanField(default=False, verbose_name='Администратор')
    is_superuser = models.BooleanField(default=False, verbose_name='Суперпользователь')
    approve_email = models.BooleanField(default=False, verbose_name='Почта подтверждена')

    name = models.CharField(max_length=100, verbose_name='Имя', blank=True)
    ROLES = (
        ('driver', 'Водитель'),
        ('master', 'Мастер'),
    )
    role = models.CharField(max_length=10, choices=ROLES, default='driver', verbose_name='Роль')
    phone = models.CharField(max_length=15, blank=True, verbose_name='Номер телефона')
    whatsapp = models.CharField(max_length=250, blank=True, verbose_name='Whatsapp')
    telegram = models.CharField(max_length=250, blank=True, verbose_name='Telegram')
    vk = models.CharField(max_length=250, blank=True, verbose_name='ВКонтакте')
    instagram = models.CharField(max_length=250, blank=True, verbose_name='Instagram')
    site = models.CharField(max_length=250, blank=True, verbose_name='Сайт')

    cars = models.ManyToManyField('api.Car', blank=True, verbose_name='Машины')
    repair_categories = models.ManyToManyField('api.RepairCategory', blank=True)

    def avatar_upload(self, filename):
        return os.path.join('users', self.email, filename)

    avatar = models.ImageField(upload_to=avatar_upload, blank=True, default=None, null=True, verbose_name='Аватар')

    REQUIRED_FIELDS = []
    USERNAME_FIELD = 'email'

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def get_name(self):
        return self.name if self.name else self.email

    def get_short_name(self):
        return self.name if self.name else self.email

    def natural_key(self):
        return self.email

    def __str__(self):
        return self.email


class OTC(models.Model):
    code = models.CharField(max_length=100, verbose_name='Код')
    key = models.CharField(max_length=100, verbose_name='Ключ')
    description = models.CharField(max_length=100, verbose_name='Описание')
    created = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Время создания')

    def __str__(self):
        return f'{self.key} ({self.code})'

    class Meta:
        verbose_name = 'Одноразовый код'
        verbose_name_plural = 'Одноразовые коды'


class CarBrand(models.Model):
    def img_upload(self, filename):
        return os.path.join('cars', 'brands', self.name, filename)

    name = models.CharField(max_length=100, verbose_name='Название', unique=True)
    img = models.ImageField(upload_to=img_upload, verbose_name='Лого')

    class Meta:
        verbose_name = 'Марка'
        verbose_name_plural = 'Марки машин'

    def __str__(self):
        return self.name


class Car(models.Model):
    brand = models.ForeignKey('api.CarBrand', on_delete=models.CASCADE, verbose_name='Марка')
    model_name = models.CharField(max_length=100, verbose_name='Название модели')

    class Meta:
        verbose_name = 'Машина'
        verbose_name_plural = 'Машины'

    def __str__(self):
        return f'{self.brand.name} {self.model_name}'


class RepairCategory(models.Model):
    name = models.CharField(max_length=50, verbose_name='Название', unique=True)
    color = models.CharField(max_length=7, verbose_name='Цвет')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'


class OfferImage(models.Model):
    def img_upload(self, filename):
        return os.path.join('offers', str(self.offer_id), filename)

    img = models.ImageField(upload_to=img_upload, verbose_name='Фотография')
    offer = models.ForeignKey('api.RepairOffer', on_delete=models.CASCADE, related_name='images',
                              verbose_name='Оффер')

    def __str__(self):
        return f'{self.offer.title} ({self.img.name})'

    class Meta:
        verbose_name = 'Картинка'
        verbose_name_plural = 'Фото офферов'


class Grade(models.Model):
    grade = models.PositiveIntegerField(default=5, validators=[MaxValueValidator(5)], verbose_name='Оценка')
    rating_user = models.ForeignKey('api.User', on_delete=models.SET_NULL, null=True, verbose_name='Оценивающий',
                                    related_name='feedback_send')
    valued_user = models.ForeignKey('api.User', on_delete=models.SET_NULL, null=True, verbose_name='Оцениваемый',
                                    related_name='feedback_receive')
    offer = models.ForeignKey('api.RepairOffer', on_delete=models.SET_NULL, null=True, default=None,
                              verbose_name='Оффер', related_name='grades')
    comment = models.TextField(verbose_name='Комментарий')
    created = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Время создания')

    def __str__(self):
        return f'{self.rating_user.name} --> {self.valued_user.name} ({self.grade})'

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'


class GradePhoto(models.Model):
    def img_upload(self, filename):
        return os.path.join('grades', str(self.grade.valued_user_id), str(self.grade_id), filename)

    img = models.ImageField(upload_to=img_upload, verbose_name='Фотография')
    grade = models.ForeignKey('api.Grade', on_delete=models.CASCADE, related_name='images', verbose_name='Отзыв')

    def __str__(self):
        return f'{self.grade.rating_user.get_short_name()} ({self.img.name})'


class Comment(models.Model):
    offer = models.ForeignKey('api.RepairOffer', on_delete=models.CASCADE, related_name='comments',
                              verbose_name='Оффер')
    reply = models.ForeignKey('api.User', on_delete=models.SET_NULL, null=True, default=None,
                              related_name='comments_replies', verbose_name='Кому ответить')
    user = models.ForeignKey('api.User', on_delete=models.CASCADE, related_name='comments',
                             verbose_name='Пользователь')
    text = models.TextField(verbose_name='Текст')
    users_liked = models.ManyToManyField('api.User', blank=True, verbose_name='Лайкнули')
    created = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Время создания')

    def __str__(self):
        return f'{self.user.name}: {self.text}'

    def reply_str(self):
        return f'@{self.reply.get_short_name()}'

    @property
    def cut_text(self):
        if len(self.text) > 150:
            return self.text[:147] + "..."
        else:
            return self.text

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Коментарии'


class CommentMedia(models.Model):
    def file_upload(self, filename):
        return os.path.join('comments', str(self.comment_id), filename)

    file = models.FileField(upload_to=file_upload, verbose_name='Файл')
    comment = models.ForeignKey('api.Comment', on_delete=models.CASCADE, related_name='media',
                                verbose_name='Коментарий')

    @property
    def extension(self):
        split_name = self.file.name.split('.')
        if len(split_name) < 2:
            return 'file'
        return split_name[-1]

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    def __str__(self):
        return self.file.name

    class Meta:
        verbose_name = 'Медиафайл'
        verbose_name_plural = 'Медиафайлы комментариев'


class RepairOffer(models.Model):
    owner = models.ForeignKey('api.User', on_delete=models.CASCADE, related_name='own_offers',
                              verbose_name='Пользователь')
    master = models.ForeignKey('api.User', on_delete=models.SET_NULL, null=True, related_name='accepted_offers',
                               verbose_name='Мастер')
    title = models.CharField(max_length=100, verbose_name='Заголовок')
    categories = models.ManyToManyField('api.RepairCategory', verbose_name='Категории')
    description = models.TextField(verbose_name='Описание')
    private = models.BooleanField(default=False, verbose_name='Приватный')

    owner_grade = models.OneToOneField('api.Grade', on_delete=models.SET_NULL, null=True,
                                       verbose_name='Отзыв владельца', related_name='owners_offer')
    master_grade = models.OneToOneField('api.Grade', on_delete=models.SET_NULL, null=True,
                                        verbose_name='Отзыв мастера', related_name='masters_offer')
    views = models.ManyToManyField('api.User', blank=True, verbose_name='Просмотрели')
    created = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Время создания')
    canceled_masters = models.ManyToManyField('api.User', related_name='canceled_offers', blank=True,
                                              verbose_name='Отказавшиеся мастера')

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.owner_id == self.master_id:
            raise SelfAppointedOffer
        return super(RepairOffer, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Оффер'
        verbose_name_plural = 'Офферы'


class Chat(models.Model):
    name = models.CharField(max_length=100, verbose_name='Имя', blank=True)
    object_id = models.CharField(max_length=255, verbose_name='ID объекта')
    object_type = models.CharField(max_length=1000, verbose_name='Тип объекта')
    created_user = models.ForeignKey('api.User', on_delete=models.SET_NULL, null=True, verbose_name='Создатель чата')
    participants = models.ManyToManyField('api.User', verbose_name='Участники', related_name='chats')
    private = models.BooleanField(default=False, verbose_name='Приватный')
    deleted = models.BooleanField(default=False, verbose_name='Удален')
    created = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Время создания')
    changed = models.DateTimeField(auto_now=True, verbose_name='Время последнего изменения')

    def __str__(self):
        return self.name if self.name else str(self.id)

    class Meta:
        verbose_name = "Чат"
        verbose_name_plural = "Чаты"
        ordering = ["changed"]


class Message(models.Model):
    user = models.ForeignKey('api.User', on_delete=models.SET_NULL, null=True, related_name='messages',
                             verbose_name='Пользователь')
    reply = models.ForeignKey('api.Message', on_delete=models.SET_NULL, null=True, default=None,
                              related_name='messages_replies', verbose_name='Кому ответить')
    have_read = models.ManyToManyField('api.User', blank=True, related_name='read_messages', verbose_name='Прочитали')
    chat = models.ForeignKey('api.Chat', on_delete=models.CASCADE, verbose_name='Чат')
    text = models.TextField(verbose_name='Текст')
    created = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Время создания')
    changed = models.DateTimeField(auto_now=True, verbose_name='Время последнего изменения')
    deleted = models.BooleanField(default=False, verbose_name='Удалено')
    tech = models.BooleanField(default=False, verbose_name='Техническое')

    @staticmethod
    def get_unread_count(user):
        return Message.objects.filter(chat__participants=user).exclude(have_read=user).count()

    @property
    def cut_text(self):
        if len(self.text) > 1100:
            return self.text[:1097] + "..."
        else:
            return self.text

    def reply_str(self):
        if self.reply:
            return self.reply.cut_text
        return ""

    def __str__(self):
        return self.text

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ["-created"]


class MessageMedia(models.Model):
    def upload_message_media_file(self, filename):
        return os.path.join("chats", str(self.message.chat.pk), "media", filename)

    file = models.FileField(upload_to=upload_message_media_file, verbose_name='Файл')
    message = models.ForeignKey('api.Message', on_delete=models.CASCADE, related_name="media", verbose_name='Сообщение')

    @property
    def extension(self):
        split_name = self.file.name.split('.')
        if len(split_name) < 2:
            return 'file'
        return split_name[-1]

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    def __str__(self):
        return self.file.name

    class Meta:
        verbose_name = 'Медиафайл'
        verbose_name_plural = 'Медиафайлы сообщений'


class SubscriptionPlan(models.Model):
    DURATION_TYPES = (
        ('day', 'День'),
        ('mon', 'Месяц'),
        ('yer', 'Год'),
    )

    ROLES = (
        ('driver', 'Водитель'),
        ('master', 'Мастер'),
        ('any', 'Любая'),
    )

    def upload_img(self, filename):
        return os.path.join('subscriptions_plans', str(self.id), filename)

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=100, unique=True)
    role = models.CharField(max_length=10, choices=ROLES, default='any')
    description = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10)
    duration = models.PositiveIntegerField(default=30)
    duration_type = models.CharField(default='day', choices=DURATION_TYPES, max_length=10)
    disabled = models.BooleanField(default=False)
    default = models.BooleanField(default=False)
    actions = models.ManyToManyField('api.SubscriptionAction', blank=True)
    img = models.ImageField(upload_to=upload_img, default=None, null=True)

    active_date_start = models.DateField(default=None, null=True, blank=True)
    active_date_end = models.DateField(default=None, null=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.default:
            SubscriptionPlan.objects.exclude(id=self.id).update(default=False)
        if not SubscriptionPlan.objects.exclude(id=self.id).exists():
            self.default = True
        return super(SubscriptionPlan, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'План подписки'
        verbose_name_plural = 'Планы подписок'


class SubscriptionAction(models.Model):
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=100)
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name + ': ' + self.value

    class Meta:
        verbose_name = 'Функционал подписки'
        verbose_name_plural = 'Функционал подписок'


class Subscription(models.Model):
    payment_id = models.CharField(max_length=200)
    start = models.DateField(default=None, null=True)
    expiration_date = models.DateField(default=None, null=True)
    user = models.ForeignKey('api.User', on_delete=models.SET_NULL, null=True)
    plan = models.ForeignKey('api.SubscriptionPlan', on_delete=models.CASCADE)
    value = models.CharField(max_length=100)
    active = models.BooleanField(default=False)

    def __str__(self):
        return f"USER: {self.user.__str__()} ({self.start} - {self.expiration_date})"

    @staticmethod
    def has_active(user):
        n = timezone.now().date()
        return Subscription.objects.filter(user=user, active=True, start__gte=n, expiration_date__gt=n).exists()

    @staticmethod
    def cancel_active(user):
        n = timezone.now().date()
        Subscription.objects.filter(user=user, active=True, start__lte=n, expiration_date__gt=n).update(active=False)

    @staticmethod
    def get_active(user):
        n = timezone.now().date()
        sub = Subscription.objects.filter(user=user, active=True, start__lte=n, expiration_date__gt=n).first()
        if sub:
            if sub.subscriptionfreeze_set.filter(start__lte=n, end__gte=n).exists():
                return None
        return sub

    @staticmethod
    def check_action(user, action: str, raise_exception=True):
        active_subscription = Subscription.get_active(user)
        if active_subscription:
            plan = active_subscription.plan
        else:
            plan = SubscriptionPlan.objects.get(default=True)
        if not plan:
            return False
        check = plan.actions.filter(code=action).exists()
        if not check and raise_exception:
            raise Forbidden('Действие недоступно в рамках текущей подписки')
        return check

    @property
    def is_freeze(self):
        n = timezone.now().date()
        return self.subscriptionfreeze_set.filter(start__lte=n, end__gte=n).exists()

    def save(self, *args, **kwargs):
        if self.user.subscription_set.exclude(id=self.id).exclude(active=False).filter(
                models.Q(start__lte=self.start, expiration_date__gte=self.start) |
                models.Q(start__gte=self.start, expiration_date__lte=self.expiration_date) |
                models.Q(start__lt=self.expiration_date, expiration_date__gte=self.expiration_date) |
                models.Q(start__lte=self.start, expiration_date__gte=self.expiration_date)
        ).exists():
            raise BadRequest('Подписки пересекаются')
        return super(Subscription, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        ordering = ["-id"]


class SubscriptionFreeze(models.Model):
    subscription = models.ForeignKey('api.Subscription', on_delete=models.CASCADE)
    renew_subscription = models.BooleanField(default=False)
    start = models.DateField()
    end = models.DateField()

    def __str__(self):
        return f'{self.subscription.user.name} ({self.start} - {self.end})'

    # @transaction.atomic
    # def save(self, *args, **kwargs):
    #     if not self.id:
    #         if self.renew_subscription:
    #             delta = relativedelta(self.start, self.end)
    #             for sub in self.subscription.user.subscription_set.filter(start__gte=self.start):
    #                 sub.start += delta
    #                 sub.end += delta
    #                 sub.save()
    #     return super(SubscriptionFreeze, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Заморозка'
        verbose_name_plural = 'Заморозки'


post_delete.connect(file_model_delete, sender=CommentMedia)
post_delete.connect(file_model_delete, sender=MessageMedia)
post_delete.connect(img_model_delete, sender=CarBrand)
post_delete.connect(img_model_delete, sender=OfferImage)
post_delete.connect(img_model_delete, sender=GradePhoto)
post_delete.connect(img_model_delete, sender=SubscriptionPlan)
post_delete.connect(user_avatar_delete, sender=User)

post_save.connect(create_helpdesk_chat, sender=User)
