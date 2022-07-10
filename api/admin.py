from django.contrib import admin

from .models import User
from .models import Car
from .models import CarBrand
from .models import RepairCategory

from django.contrib import admin

from .models import Subscription
from .models import SubscriptionFreeze
from .models import SubscriptionPlan
from .models import SubscriptionAction


class SubscriptionFreezeInline(admin.StackedInline):
    model = SubscriptionFreeze
    fk_name = 'subscription'
    extra = 0


class SubscriptionAdmin(admin.ModelAdmin):
    def is_freeze(self, obj):
        if obj.is_freeze:
            return 'ДА'
        return 'НЕТ'

    model = Subscription
    list_display = ("user", 'plan', 'start', 'expiration_date', 'value', 'active', 'is_freeze', 'payment_id')
    list_filter = ("plan", "active",)
    fieldsets = (
        (None, {
            'fields': (('user', 'plan',), ('start', 'expiration_date',), 'active',),
        }),
    )
    add_fieldsets = (
        (None, {
            'fields': (('user', 'plan',), ('start', 'expiration_date',), 'active',),
        }),
    )
    search_fields = ("user__name", "plan__name", "plan__description")
    ordering = ("user", 'plan', 'start', 'expiration_date', 'value', 'active', 'payment_id')
    inlines = (SubscriptionFreezeInline,)


class SubscriptionPlanAdmin(admin.ModelAdmin):
    model = SubscriptionPlan
    list_display = ('name', 'role', 'code', 'cost', 'currency', 'duration', 'duration_type', 'description',)
    list_filter = ('disabled', 'default', 'duration_type', 'role',)
    fieldsets = (
        (None, {
            'fields': (
                ('name', 'code', 'role'),
                ('duration', 'duration_type',),
                ('description',),
                ('cost', 'currency',),
                ('disabled', 'default',),
                ('img',),
            )
        }),
        ('Функционал', {
            'fields': ('actions',)
        })
    )
    filter_horizontal = ('actions',)
    search_fields = ('name', 'role', 'code', 'cost', 'currency', 'description',)
    ordering = ('name', 'role', 'code', 'cost', 'currency', 'duration', 'duration_type', 'description',)


class SubscriptionActionAdmin(admin.ModelAdmin):
    model = SubscriptionAction
    list_display = ('name', 'value', 'code', 'description',)
    search_fields = ('name', 'value', 'code', 'description',)
    ordering = ('name', 'value', 'code', 'description',)


admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(SubscriptionPlan, SubscriptionPlanAdmin)
admin.site.register(SubscriptionAction, SubscriptionActionAdmin)

admin.site.register(User)
admin.site.register(Car)
admin.site.register(CarBrand)
admin.site.register(RepairCategory)
