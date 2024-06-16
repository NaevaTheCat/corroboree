from django.db import models

from wagtail.models import Page

from wagtail.snippets.models import register_snippet

from corroboree.config import models as config
@register_snippet
class BookingRecord(models.Model):
    class BookingRecordStatus(models.TextChoices):
        IN_PROGRESS = "PR"
        SUBMITTED = "SB"
        FINALISED = "FN"
        CANCELLED = "CX"

    class BookingRecordPaymentStatus(models.TextChoices):
        ISSUED = "IS"
        PAID = "PD"
        FAILED = "FL"
        REFUNDED = "RF"

    member = models.ForeignKey(config.Member, on_delete=models.PROTECT, related_name="bookings")
    last_updated = models.DateTimeField(auto_now=True)
    start_date = models.DateField()
    end_date = models.DateField()
    rooms = models.ManyToManyField(config.Room)
    member_in_attendance = models.ForeignKey(config.FamilyMember, on_delete=models.PROTECT, related_name="bookings")
    other_attendees = models.JSONField(default=dict) #{{first:, last:, contact:}}
    cost = models.DecimalField(max_digits=8, decimal_places=2)
    payment_status = models.CharField(max_length=2, choices=BookingRecordPaymentStatus)
    status = models.CharField(max_length=2, choices=BookingRecordStatus)

class BookingPage(Page):
    pass