from django.contrib.auth.models import AbstractUser
from django.db import models

from corroboree.config import models as config


class MemberAccount(AbstractUser):
    member = models.OneToOneField(config.Member, on_delete=models.SET_NULL, null=True, blank=True, related_name="member_account")
