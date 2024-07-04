from django.db import models
from django.shortcuts import render

from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel

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
    other_attendees = models.JSONField(default=dict)  # {{first:, last:, contact:}}
    cost = models.DecimalField(max_digits=8, decimal_places=2)
    payment_status = models.CharField(max_length=2, choices=BookingRecordPaymentStatus)
    status = models.CharField(max_length=2, choices=BookingRecordStatus)


class BookingPage(Page):
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    def serve(self, request):
        from corroboree.booking.forms import BookingDateRangeForm, BookingRoomChoosingForm

        if request.method == "POST":
            form = BookingDateRangeForm(request.POST)
            if form.is_valid():
                start_date = form.cleaned_data.get("start_date")
                end_date = form.cleaned_data.get("end_date")
                form = BookingRoomChoosingForm(start_date=start_date, end_date=end_date)
        else:
            form = BookingDateRangeForm()

        return render(request, 'booking/select_dates.html', {
            "page": self,
            "form": form,
        })


class BookingCalendar(Page):
    pass
