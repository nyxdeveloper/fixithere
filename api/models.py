from django.db import models
from django.contrib.auth.models import PermissionsMixin, AbstractBaseUser, BaseUserManager
from django.core.validators import MaxValueValidator
from django.db.models.signals import post_delete

from .signals import file_model_delete
from .signals import img_model_delete
from .signals import user_avatar_delete

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
    comment = models.TextField(verbose_name='Комментарий')
    created = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Время создания')

    def __str__(self):
        return f'{self.rating_user.name} --> {self.valued_user.name} ({self.grade})'

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'


class GradePhoto(models.Model):
    def img_upload(self, filename):
        if self.owners_offer:
            offer_id = self.owners_offer_id
        elif self.masters_offer:
            offer_id = self.masters_offer_id
        else:
            raise Exception('Grade must be attached an offer from owner or master.')
        return os.path.join('offers', str(offer_id), 'grades', filename)

    img = models.ImageField(upload_to=img_upload, verbose_name='Фотография')
    grade = models.ForeignKey('api.Grade', on_delete=models.CASCADE, related_name='images',
                              verbose_name='Отзыв')

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

    def __str__(self):
        return self.title

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
    reply = models.ForeignKey('api.User', on_delete=models.SET_NULL, null=True, default=None,
                              related_name='messages_replies', verbose_name='Кому ответить')
    have_read = models.ManyToManyField('api.User', blank=True, related_name='read_messages', verbose_name='Прочитали')
    chat = models.ForeignKey('api.Chat', on_delete=models.CASCADE, verbose_name='Чат')
    text = models.TextField(verbose_name='Текст')
    created = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Время создания')
    changed = models.DateTimeField(auto_now=True, verbose_name='Время последнего изменения')
    deleted = models.BooleanField(default=False, verbose_name='Удалено')

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
        return f'@{self.reply.get_short_name()}'

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


post_delete.connect(file_model_delete, sender=CommentMedia)
post_delete.connect(file_model_delete, sender=MessageMedia)
post_delete.connect(img_model_delete, sender=CarBrand)
post_delete.connect(img_model_delete, sender=OfferImage)
post_delete.connect(img_model_delete, sender=GradePhoto)
post_delete.connect(user_avatar_delete, sender=User)
