# django
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm):
        model = User
        fields = (
            'email',
            'is_active',
            'is_staff',
            'is_superuser',
            'approve_email',
            'name',
            'role',
            'phone',
            'whatsap',
            'telegram',
            'vk',
            'instagram',
            'site',
            'car',
            'custom_car_version',
            'avatar',
            'password1',
            'password2',
        )


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = (
            'email',
            'is_active',
            'is_staff',
            'is_superuser',
            'approve_email',
            'name',
            'role',
            'phone',
            'whatsap',
            'telegram',
            'vk',
            'instagram',
            'site',
            'car',
            'custom_car_version',
            'avatar',
            'password',
        )
