from django.db import models
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect

from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel

from wagtail.snippets.models import register_snippet

import datetime

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
    member_in_attendance = models.ForeignKey(config.FamilyMember, on_delete=models.PROTECT, related_name="bookings", null=True)
    other_attendees = models.JSONField(default=dict, blank=True)  # {{first:, last:, contact:}}
    cost = models.DecimalField(max_digits=8, decimal_places=2)
    payment_status = models.CharField(max_length=2, choices=BookingRecordPaymentStatus, blank=True)
    status = models.CharField(max_length=2, choices=BookingRecordStatus)


class BookingPage(Page):
    intro = RichTextField(blank=True)
    not_authorised_message = RichTextField(blank=True)


    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("not_authorised_message")
    ]

    def serve(self, request):
        from corroboree.booking.forms import BookingDateRangeForm, BookingRoomChoosingForm
        member = request.user.member
        room_form = None
        if member is None:
            return render(request, "booking/not_authorised.html", {
                'page': self,
            })
        else:
            if request.method == "POST":
                if 'room_form' in request.POST:
                    room_form = BookingRoomChoosingForm(
                        request.POST,
                        start_date=request.POST['start_date'],
                        end_date=request.POST['end_date'],
                        member=member)
                    if room_form.is_valid():
                        # Put the booking in the database as a hold and redirect the user to finish it
                        booking_record = BookingRecord(
                            member=room_form.cleaned_data.get('member'),
                            start_date=room_form.cleaned_data.get('start_date'),
                            end_date=room_form.cleaned_data.get('end_date'),
                            member_in_attendance=None,
                            cost=100, #stub!
                            payment_status='',
                            status=BookingRecord.BookingRecordStatus.IN_PROGRESS
                        )
                        booking_record.save()
                        rooms = room_form.cleaned_data.get('room_selection')
                        #rooms = config.Room.objects.filter(room_number__in=room_form.cleaned_data.get('room_selection'))
                        booking_record.rooms.set(rooms)
                    # Preset the date values on the date form for consistency
                    start_date = room_form.data.get("start_date")
                    end_date = room_form.data.get("end_date")
                    date_form = BookingDateRangeForm(initial={
                        "start_date": start_date,
                        'end_date': end_date,
                    })
                else: #date form is returned
                    date_form = BookingDateRangeForm(request.POST)
                    if date_form.is_valid():
                        start_date = date_form.cleaned_data.get("start_date")
                        end_date = date_form.cleaned_data.get("end_date")
                        room_form = BookingRoomChoosingForm(start_date=start_date, end_date=end_date, member=member)
            else:
                date_form = BookingDateRangeForm()

            return render(request, 'booking/select_dates.html', {
                "page": self,
                "date_form": date_form,
                "room_form": room_form,
            })

@csrf_protect #superstitious? might've fixed a bug once
class BookingPageUserSummary(Page):
    intro = RichTextField(blank=True)
    no_bookings_text = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('no_bookings_text'),
    ]

    def get_context(self, request):
        context = super().get_context(request)
        if request.user.is_authenticated:
            member = request.user.member
            today = datetime.datetime.today()
            member_bookings = BookingRecord.objects.filter(
                end_date__gt=today,
                member__exact=member,
            ).exclude(
                status__exact=BookingRecord.BookingRecordStatus.CANCELLED,
            ).order_by('start_date')
            context['member_bookings'] = member_bookings
        return context


class BookingCalendar(Page):
    pass
