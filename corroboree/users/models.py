from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django_otp.plugins.otp_email.models import EmailDevice

from corroboree.config import models as config


class MemberAccount(AbstractUser):
    member = models.OneToOneField(config.Member, on_delete=models.SET_NULL, null=True, blank=True, related_name="member_account")


@receiver(post_save, sender=MemberAccount)
def initial_email_device(sender, instance, created, **kwargs):
    if created:
        EmailDevice.objects.create(user=instance, email=instance.email, name='default')


@receiver(pre_save, sender=MemberAccount)
def update_email_device(sender, instance, **kwargs):
    if instance.pk:
        old_email = MemberAccount.objects.get(pk=instance.pk).email
        if old_email != instance.email:
            EmailDevice.objects.filter(user=instance).delete()
            EmailDevice.objects.create(user=instance, email=instance.email, name='default')
