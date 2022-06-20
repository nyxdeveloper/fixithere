def file_model_delete(sender, instance, **kwargs):
    if instance.file.name:
        instance.file.delete(False)


def img_model_delete(sender, instance, **kwargs):
    if instance.img.name:
        instance.img.delete(False)


def user_avatar_delete(sender, instance, **kwargs):
    if instance.avatar.name:
        instance.avatar.delete()
