from django.db.models import Count, OuterRef, Sum, BooleanField, Subquery
from .models import Message


def chat_unread_count_annotate(queryser, user_id):
    messages = Message.objects.filter(chat=OuterRef('pk')).exclude(user_id=user_id).annotate(
        read=Sum('have_read', output_field=BooleanField())
    ).filter(read=False).order_by().values('read')
    unread_count = messages.annotate(c=Count('*')).values('c')
    return queryser.annotate(unread_count=Subquery(unread_count))
