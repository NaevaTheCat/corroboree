from django.db import models

from wagtail.snippets.models import register_snippet

from corroboree import config
@register_snippet
class BookingRecord(models.Model):
    belongs_to = models.ForeignKey(config.Member, on_delete=models.PROTECTgit)