from django.db.models import IntegerField
from django.db.models import BooleanField
from django.db.models import Count
from django.db.models import Case
from django.db.models import When
from django.db.models import Value
from django.db.models import Sum
from django.db.models import OuterRef
from django.db.models import Subquery
from django.db.models import Q
from .models import Message


def annotate_comments_likes_count(queryset):
    return queryset.annotate(users_liked_count=Count('users_liked', output_field=IntegerField()))


def annotate_repair_offers_views_count(queryset):
    return queryset.annotate(views_count=Count('views', output_field=IntegerField()))


def annotate_chats_unread_count(queryset, user_id):
    messages = Message.objects.filter(chat=OuterRef('pk')).exclude(user_id=user_id).annotate(
        read=Sum('have_read', output_field=BooleanField())
    ).filter(read=False).order_by().values('read')
    unread_count = messages.annotate(c=Count('*')).values('c')
    return queryset.annotate(unread_count=Subquery(unread_count))


def annotate_repair_offers_my_my_accept_free(queryset, user_id):
    return queryset.annotate(
        my=Case(
            When(owner_id=user_id, then=Value(True, output_field=BooleanField())),
            default=Value(False, output_field=BooleanField())
        ),
        my_accept=Case(
            When(master_id=user_id, then=Value(True, output_field=BooleanField())),
            default=Value(False, output_field=BooleanField())
        ),
        free=Case(
            When(master__isnull=False, then=Value(False, output_field=BooleanField())),
            When(owner_id=user_id, then=Value(False, output_field=BooleanField())),
            default=Value(True, output_field=BooleanField())
        )
    )


def annotate_repair_offers_completed(queryset):
    return queryset.annotate(completed=Case(
        When(Q(owner_grade__isnull=False, master_grade__isnull=False), then=Value(True, BooleanField())),
        default=Value(False, BooleanField())
    ))
