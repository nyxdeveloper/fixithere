def file_model_delete(sender, instance, **kwargs):
    if instance.file.name:
        instance.file.delete(False)


def img_model_delete(sender, instance, **kwargs):
    if instance.img.name:
        instance.img.delete(False)


def user_avatar_delete(sender, instance, **kwargs):
    if instance.avatar.name:
        instance.avatar.delete()


def faq_content_background_delete(sender, instance, **kwargs):
    if instance.background_img.name:
        instance.background_img.delete()


def create_helpdesk_chat(sender, instance, created, **kwargs):
    if created:
        hd_chat = instance.chats.create(
            object_id=str(instance.pk),
            object_type='helpdesk',
            created_user=instance,
            private=True
        )
        hd_chat.participants.add(instance.id)
