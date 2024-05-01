from django.db import models

from wagtail.snippets.models import register_snippet

from corroboree.config import models as config
@register_snippet
class BookingRecord(models.Model):
    belongs_to = models.ForeignKey(config.Member, on_delete=models.PROTECT)