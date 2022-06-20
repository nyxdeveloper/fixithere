from django.db.models import Count
from django.db.models import IntegerField


def annotate_comments_likes_count(queryset):
    return queryset.annotate(users_liked_count=Count('users_liked', output_field=IntegerField()))


def annotate_repair_offers_views_count(queryset):
    return queryset.annotate(views_count=Count('views', output_field=IntegerField()))
