from django.contrib import admin

from .models import User
from .models import Car
from .models import CarBrand

admin.site.register(User)
admin.site.register(Car)
admin.site.register(CarBrand)
