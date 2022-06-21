from django.db.models import IntegerField
from django.db.models import BooleanField
from django.db.models import Count
from django.db.models import Sum
from django.db.models import OuterRef
from django.db.models import Subquery
from .models import Message


def annotate_comments_likes_count(queryset):
    return queryset.annotate(users_liked_count=Count('users_liked', output_field=IntegerField()))


def annotate_repair_offers_views_count(queryset):
    return queryset.annotate(views_count=Count('views', output_field=IntegerField()))


def annotate_chats_unread_count(queryser, user_id):
    messages = Message.objects.filter(chat=OuterRef('pk')).exclude(user_id=user_id).annotate(
        read=Sum('have_read', output_field=BooleanField())
    ).filter(read=False).order_by().values('read')
    unread_count = messages.annotate(c=Count('*')).values('c')
    return queryser.annotate(unread_count=Subquery(unread_count))
