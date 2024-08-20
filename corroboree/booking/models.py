import datetime
from datetime import date, datetime, timedelta

from django.core.mail import send_mail
from django.db import models
from django.db.models import Sum
from django.forms import formset_factory
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_protect
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.fields import RichTextField
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
        NOT_ISSUED = 'NI'

    member = models.ForeignKey(config.Member, on_delete=models.PROTECT, related_name="bookings")
    last_updated = models.DateTimeField(auto_now=True)
    start_date = models.DateField()
    end_date = models.DateField()
    rooms = models.ManyToManyField(config.Room)
    member_in_attendance = models.ForeignKey(config.FamilyMember, on_delete=models.PROTECT, related_name="bookings",
                                             null=True)
    other_attendees = models.JSONField(default=dict, blank=True)  # {{first:, last:, contact:}}
    cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    payment_status = models.CharField(max_length=2, choices=BookingRecordPaymentStatus, default=BookingRecordPaymentStatus.NOT_ISSUED)
    status = models.CharField(max_length=2, choices=BookingRecordStatus)

    def calculate_booking_cart(self, conf: config.Config):
        booking_types = get_booking_types(conf, self.start_date, self.end_date)
        cost = 0
        for day in booking_types:
            # add the cost of the highest (smallest int) priority booking
            cost += booking_types[day].exclude(
                banned_rooms__in=self.rooms.all()).exclude(
                minimum_rooms__gt=self.rooms.count()).order_by('priority_rank').first().rate
        self.cost = cost
        self.save()


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
                        start_date=date.fromisoformat(request.POST['start_date']),
                        end_date=date.fromisoformat(request.POST['end_date']),
                        member=member)
                    if room_form.is_valid():
                        # Put the booking in the database as a hold and redirect the user to finish it
                        booking_record = BookingRecord(
                            member=room_form.cleaned_data.get('member'),
                            start_date=room_form.cleaned_data.get('start_date'),
                            end_date=room_form.cleaned_data.get('end_date'),
                            member_in_attendance=None,
                            cost=None,
                            payment_status=BookingRecord.BookingRecordPaymentStatus.NOT_ISSUED,
                            status=BookingRecord.BookingRecordStatus.IN_PROGRESS
                        )
                        booking_record.save()
                        rooms = room_form.cleaned_data.get('room_selection')
                        booking_record.rooms.set(rooms)
                        booking_record.calculate_booking_cart(config.Config.objects.get())
                        return redirect('/my-bookings/edit/%s' % booking_record.pk)
                    # Preset the date values on the date form for consistency
                    start_date = room_form.data.get("start_date")
                    end_date = room_form.data.get("end_date")
                    date_form = BookingDateRangeForm(initial={
                        "start_date": start_date,
                        'end_date': end_date,
                    })
                else:  # date form is returned
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


@csrf_protect  # superstitious? might've fixed a bug once
class BookingPageUserSummary(RoutablePageMixin, Page):
    in_progress_text = RichTextField(blank=True,
                                   help_text='Text to introduce bookings that need to be completed if any exit')
    submitted_text = RichTextField(blank=True,
                                   help_text='Text to introduce bookings that have been submitted but not confirmed/paid')
    upcoming_text = RichTextField(blank=True,
                                  help_text='Text to introduce upcoming bookings if any exist')
    edit_text = RichTextField(blank=True,
                              help_text='Text to display when editing a booking')
    not_found_text = RichTextField(blank=True,
                                      help_text='Text to display when linked booking is not theirs or editable')
    no_bookings_text = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        MultiFieldPanel(heading='Booking Summary Page', children=(
            FieldPanel('no_bookings_text'),
            FieldPanel('in_progress_text'),
            FieldPanel('submitted_text'),
            FieldPanel('upcoming_text'),
        )),
        MultiFieldPanel(heading='Booking Edit Page', children=(
            FieldPanel('edit_text'),
            FieldPanel('not_found_text'),
        )),
    ]

    @path('')
    def booking_index_page(self, request):
        if request.user.is_authenticated:
            member = request.user.member
            today = date.today()
            bookings = BookingRecord.objects.filter(member__exact=member)
            upcoming_bookings = bookings.filter(
                end_date__gt=today,
                status__exact=BookingRecord.BookingRecordStatus.FINALISED
            ).order_by('start_date')
            in_progress_bookings = bookings.filter(
                status__exact=BookingRecord.BookingRecordStatus.IN_PROGRESS
            ).order_by('start_date')
            submitted_bookings = bookings.filter(
                status__exact=BookingRecord.BookingRecordStatus.SUBMITTED
            ).order_by('start_date')
            return self.render(request, context_overrides={
                'title': 'My Bookings',
                'upcoming_bookings': upcoming_bookings,
                'in_progress_bookings': in_progress_bookings,
                'submitted_bookings': submitted_bookings,
            })

    @path('edit/<int:booking_id>/')
    def booking_edit_page(self, request, booking_id=None):
        from corroboree.booking.forms import BookingRecordMemberInAttendanceForm, GuestForm
        if request.user.is_authenticated:
            member = request.user.member
            if booking_id is None:
                booking_id = BookingRecord.objects.filter(member=member).order_by('last_updated').first()
            # Try find the booking, but make sure it's ours and editable!
            try:
                booking = BookingRecord.objects.get(
                    pk=booking_id,
                    member=member,
                    status=BookingRecord.BookingRecordStatus.IN_PROGRESS
                )
            except BookingRecord.DoesNotExist:  # Due to using PK no need to catch multiple objects
                booking = None
                return self.render(request, template='booking/booking_not_found.html')
            # make a form
            member_in_attendance_form = BookingRecordMemberInAttendanceForm()
            max_attendees = booking.rooms.aggregate(max_occupants=Sum('room_type__max_occupants'))['max_occupants']
            GuestFormSet = formset_factory(GuestForm, extra=max_attendees - 1)
            if request.method == 'POST':  # User has submitted the guest form
                guest_forms = GuestFormSet(request.POST)
                member_in_attendance_form = BookingRecordMemberInAttendanceForm(request.POST)
                if guest_forms.is_valid() and member_in_attendance_form.is_valid():
                    guest_list = []
                    for guest in guest_forms:
                        guest_list.append({
                            'first_name': guest.cleaned_data.get('first_name', ''),
                            'last_name': guest.cleaned_data.get('last_name', ''),
                            'email_contact': guest.cleaned_data.get('email', ''),
                        })
                    other_attendees = {'other_attendees': guest_list}
                    member_in_attendance = member_in_attendance_form.cleaned_data['member_in_attendance']
                    booking.member_in_attendance = member_in_attendance
                    booking.other_attendees = other_attendees
                    booking.status = BookingRecord.BookingRecordStatus.SUBMITTED
                    booking.save()
                    return redirect(self.url + 'pay/%s' % booking_id)
            else:
                guest_forms = GuestFormSet()
            return self.render(request,
                               context_overrides={
                                   'title': 'Edit Booking',
                                   'booking': booking,
                                   'member_in_attendance_form': member_in_attendance_form,
                                   'guest_forms': guest_forms,
                               },
                               template='booking/edit_booking.html',
                               )
    @path('pay/<int:booking_id>/')
    def booking_payment_page(self, request, booking_id=None):
        if request.user.is_authenticated:
            member = request.user.member
            if booking_id is None:
                booking_id = BookingRecord.objects.filter(member=member).order_by('last_updated').first()
            try:
                booking = BookingRecord.objects.get(
                    pk=booking_id,
                    member=member,
                    status=BookingRecord.BookingRecordStatus.SUBMITTED,
                    payment_status=BookingRecord.BookingRecordPaymentStatus.NOT_ISSUED,  # Maybe need failed? if
                    # that's even needed
                )
            except BookingRecord.DoesNotExist:  # Due to using PK no need to catch multiple objects
                booking = None
                return self.render(request, template='booking/booking_not_found.html')  # TODO: Mod template for url message
            return self.render(request,
                               context_overrides={
                                   'title': 'Confirm and Pay',
                                   'booking': booking,
                               },
                               template='booking/pay_booking.html',
                               )
class BookingCalendar(Page):
    pass


def bookings_for_member_in_range(member: config.Member, start_date: date, end_date: date):
    """Given a member and a date range returns bookings for that member within that date range (including partially)"""
    bookings = member.bookings.exclude(end_date__lte=start_date).exclude(start_date__gte=end_date)
    return bookings


def dates_to_weeks(start_date: date, end_date: date, week_start_day=6) -> (int, int, int):
    """For a date range and day of week return the number of weeks and surrounding 'spare' days

    Using datetime weekday ints monday=0 sunday=6.
    """
    start_weekday = start_date.weekday()
    end_weekday = end_date.weekday()
    leading_days = (week_start_day - start_weekday) % 7
    trailing_days = (7 - (week_start_day - end_weekday)) % 7
    from_week = start_date + timedelta(days=leading_days)
    till_week = end_date - timedelta(days=trailing_days)
    weeks = int((till_week - from_week).days / 7)
    return leading_days, weeks, trailing_days


def get_booking_types(conf: config.Config, start_date: date, end_date: date):
    """Returns a dictionary of date-keyed booking type querysets with dates matching either a week start or a 'spare' day

    Assumes that a week has a weekly booking type. Will not return daily bookings for week-equivalent dates"""
    leading_days, weeks, trailing_days = dates_to_weeks(start_date, end_date)
    seasons = list(conf.seasons_in_date_range(start_date, end_date))
    leading_dates = [start_date + timedelta(days=x) for x in range(leading_days)]
    week_dates = [start_date + timedelta(days=leading_days + x * 7) for x in range(weeks)]
    trailing_dates = [start_date + timedelta(days=7 * weeks + leading_days + x) for x in range(trailing_days)]
    booking_types = {}
    for day in leading_dates:
        season_on_day = seasons_to_season_on_day(seasons, day)
        booking_types[day] = season_on_day.booking_types.exclude(is_full_week_only=True)  # This is a single day
    for week_start in week_dates:
        season_on_day = seasons_to_season_on_day(seasons, week_start)
        booking_types[week_start] = season_on_day.booking_types.filter(is_full_week_only=True)  # Only the weekly ones
    for day in trailing_dates:
        season_on_day = seasons_to_season_on_day(seasons, day)
        booking_types[day] = season_on_day.booking_types.exclude(is_full_week_only=True)
    return booking_types


def seasons_to_season_on_day(seasons: [config.Season], day: date) -> config.Season:
    """Take a list of seasons and return the single season active on the day.

    Helper function to avoid multiple database hits when querying bookings"""
    season_on_day = [s for s in seasons if s.date_is_in_season(day)]
    if len(season_on_day) == 1:
        season_on_day = season_on_day[0]
    elif len(season_on_day) == 2:
        season_on_day = [s for s in season_on_day if s.season_is_peak][0]  # get only the peak season
    else:
        raise ValueError('Somehow multiple seasons apply?: %s' % season_on_day)
    return season_on_day


def send_confirmation_email(booking: BookingRecord):  # TODO: do less in the template, more here in the context
    """Format and send an email using a django template"""
    subject = 'Neige Booking Confirmation: {start} - {end}'.format(
        start=booking.start_date,
        end=booking.end_date,
    )
    from_email = 'Neige <neige.email@example.com>'
    to_email = booking.member.contact_email
    html_message = render_to_string('email/confirmation_mail_template.html', {'booking': booking})
    plain_message = strip_tags(html_message)
    send_mail(
        subject,
        plain_message,
        from_email,
        [to_email],
        html_message=html_message,
    )
