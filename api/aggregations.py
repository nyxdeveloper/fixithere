from django.db.models import IntegerField
from django.db.models import BooleanField
from django.db.models import FloatField
from django.db.models import Count
from django.db.models import Case
from django.db.models import When
from django.db.models import Value
from django.db.models import Exists
from django.db.models import Sum
from django.db.models import OuterRef
from django.db.models import Subquery
from django.db.models import Q
from django.db.models import F
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


def annotate_masters_statistic(queryset):
    return queryset.annotate(
        complete_offers_count=Count('accepted_offers', Q(accepted_offers__owner_grade__isnull=False)),
        # canceled_offers_count=Count('canceled_offers'),
        # all_offers_count=F('complete_offers_count') + F('canceled_offers_count'),
        # trusting_users_count=Count('trusting_users'),
        # requested_cooperation_count=Count('requested_cooperation', Q(requested_cooperation__positive_response=True)),
        # responded_cooperation_count=Count('requested_cooperation', Q(responded_cooperation__positive_response=True)),
        # cooperation_count=F('requested_cooperation_count') + F('responded_cooperation_count'),
        feedback_count=Count('feedback_receive'),
        rating=Case(
            When(Q(feedback_count=0), then=0.0),
            default=Sum('feedback_receive__grade') / Count('feedback_receive'),
            output_field=FloatField()
        ),
        # offer_complete_percent=Case(
        #     When(Q(all_offers_count=0), then=0.0),
        #     default=F('complete_offers_count') / F('all_offers_count') * Value(100),
        #     output_field=FloatField()
        # )
    )


def annotate_masters_is_trusted(queryset, user):
    return queryset.annotate(is_trusted=Exists(user.trusted_masters.filter(pk=OuterRef('pk'))))
