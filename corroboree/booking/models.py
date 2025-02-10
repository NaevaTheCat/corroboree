import datetime
from datetime import date, datetime, timedelta

import pytz
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.mail import send_mail
from django.db import models
from django.db.models import Sum, Q, QuerySet
from django.forms import formset_factory
from django.http import Http404
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_protect
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.fields import RichTextField
from wagtail.models import Page

from corroboree.config import models as config
from corroboree.config.models import Season, Room, BookingType


class LiveBookingRecordManager(models.Manager):
    """Filters out records which are not live from querysets.

    Live means that they have not been cancelled, expired, or taken place in the past"""

    def get_queryset(self):
        status = BookingRecord.BookingRecordStatus
        now = timezone.now()
        # TODO: settings?
        in_progress_limit = now - timedelta(minutes=30)
        submitted_limit = now - timedelta(hours=24)
        queryset = super().get_queryset().exclude(status=status.CANCELLED)
        queryset = queryset.exclude(
            Q(status=status.IN_PROGRESS) &
            Q(last_updated__lt=in_progress_limit)
        )
        queryset = queryset.exclude(
            Q(status=status.SUBMITTED) &
            Q(last_updated__lt=submitted_limit)
        )
        return queryset


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
    member_name_at_creation = models.CharField(max_length=128,
                                               help_text="The name of the original member who booked. "
                                                         "Used for record keeping when shares are transferred")
    last_updated = models.DateTimeField(auto_now=True)
    arrival_date = models.DateField()
    departure_date = models.DateField()
    rooms = models.ManyToManyField(config.Room)
    member_in_attendance = models.ForeignKey(config.FamilyMember, on_delete=models.PROTECT, related_name="bookings",
                                             null=True)
    member_in_attendance_name_at_creation = models.CharField(max_length=128,
                                                             blank=True,
                                                             help_text="The name of the original member who booked. "
                                                                       "Used for record keeping when shares are transferred")
    other_attendees = models.JSONField(default=dict, blank=True)  # {guest_n: {first_name:, last_name:, contact_email:}}
    cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    payment_status = models.CharField(max_length=2, choices=BookingRecordPaymentStatus,
                                      default=BookingRecordPaymentStatus.NOT_ISSUED)
    paypal_transaction_id = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=2, choices=BookingRecordStatus)
    reminder_sent = models.BooleanField(default=False)
    send_admin_email = models.BooleanField(default=False, help_text="Mark this True if an email should be sent "
                                                                    "indicating that an administrator created or "
                                                                    "tinkered with this booking")

    objects = models.Manager()
    live_objects = LiveBookingRecordManager()

    def __str__(self):
        return '[{id}] {start} - {end}: {member}'.format(
            id=self.pk,
            start=self.arrival_date,
            end=self.departure_date,
            member=self.member,
        )

    def rooms_list(self):
        rooms = list(self.rooms.all())
        return ', '.join(str(r) for r in rooms)

    def calculate_booking_cart(self):
        periods = create_booking_cart_periods(self.arrival_date, self.departure_date)
        cost = 0
        for p in periods:
            p.set_rooms(self.rooms.all())
            p.set_cost()
            cost = cost + p.cost
        self.cost = cost
        self.save()
    # TODO: Proper workflow n shit for the periods and showing them. Serialise?
    def explain_booking_cart(self):  # Temporary generator
        periods = create_booking_cart_periods(self.arrival_date, self.departure_date)
        strs = []
        for p in periods:
            p.set_rooms(self.rooms.all())
            p.set_cost()
            strs.append(str(p))
        return strs

    def update_payment_status(self, status: BookingRecordPaymentStatus, transaction_id=None):
        # TODO: validate allowed state transition
        self.payment_status = status
        if transaction_id is not None:
            self.paypal_transaction_id = transaction_id
        self.save()

    def update_status(self, status: BookingRecordStatus):
        # TODO: validate allowed state transitions
        self.status = status
        self.save()

    def send_related_email(self, subject, email_text):
        """Format and send an email using a django template"""
        from_email = settings.BOOKING_FROM_EMAIL
        recipients = [self.member.contact_email]
        if self.member_in_attendance.contact_email != self.member.contact_email:
            recipients.append(self.member_in_attendance.contact_email)
        attendees = list(self.other_attendees.values())
        attendees = [x for x in attendees if
                     x['first_name'] != '' and x['last_name'] != '' and x['email'] != '']
        html_message = render_to_string(
            'email/confirmation_mail_template.html',
            {'booking': self, 'email_text': email_text, 'attendees': attendees}
        )
        plain_message = strip_tags(html_message)
        send_mail(
            subject,
            plain_message,
            from_email,
            recipients,
            html_message=html_message,
        )



class BookingCartPeriod:
    def __init__(self, start_date: date, end_date: date, start_season: Season, end_season: Season,
                 is_full_week: bool, is_flexible_period: bool, is_last_minute_period: bool):
        self.start_date = start_date
        self.end_date = end_date
        self.start_season = start_season
        self.end_season = end_season
        self.is_full_week = is_full_week
        self.is_flexible_period = is_flexible_period
        self.is_last_minute_period = is_last_minute_period
        self.rooms = None
        self.valid_booking_types = (None, None)
        self.booking_type = None
        self.cost = None
        self.set_valid_booking_types()

    def __repr__(self):
        return (f"BookingPeriod(start_date={self.start_date}, end_date={self.end_date}, "
                f"start_season={self.start_season}, end_season={self.end_season}, "
                f"is_full_week={self.is_full_week}, "
                f"is_flexible_period={self.is_flexible_period}, "
                f"is_last_minute_period={self.is_last_minute_period}, "
                f"booking_type={self.booking_type}, cost={self.cost})")

    def __str__(self):
        return (f"Period: {self.start_date} - {self.end_date}, "
                f"Rate: {self.booking_type}, Rooms: {self.rooms.count()}, "
                f"Cost ${self.cost}")

    def set_rooms(self, rooms: QuerySet[Room]):
        self.rooms = rooms

    def set_cost(self):
        booking_types, _ = self.valid_booking_types
        filtered_booking_types = booking_types.exclude(banned_rooms__in=self.rooms).exclude(minimum_rooms__gt=self.rooms.count())
        self.booking_type = filtered_booking_types.order_by('priority_rank').first()
        if self.booking_type.is_full_week_only:
            per_room_cost = self.booking_type.rate
        else:
            per_room_cost = self.booking_type.rate * (self.end_date - self.start_date).days
            # Cap daily rates to maximum
            try:
                capping_type = self.start_season.booking_types.get(sets_weekly_rate_cap=True)
                per_room_cost = min(per_room_cost, capping_type.rate)
            except BookingType.DoesNotExist:
                pass
        if self.booking_type.is_flat_rate:
            self.cost = per_room_cost
        else:
            self.cost = per_room_cost * self.rooms.count()

    def set_valid_booking_types(self):
        booking_types = self.start_season.booking_types.all()
        # Filter down to possible type
        filtered_booking_types = booking_types
        if not self.is_full_week:
            filtered_booking_types = filtered_booking_types.exclude(is_full_week_only=True)
        if not self.is_flexible_period:
            filtered_booking_types = filtered_booking_types.exclude(requires_flexible_booking_period=True)
        if not self.is_last_minute_period:
            filtered_booking_types = filtered_booking_types.exclude(requires_last_minute_booking_period=True)
        # Make sure any portions in a new season don't violate room restrictions
        if self.start_season != self.end_season:
            end_season_booking_types = self.end_season.booking_types.all()
            # Need to check whether this is a full week under the new season
            if self.end_season.requires_strict_weeks and not self.is_last_minute_period:
                week_start_day = self.end_season.config.week_start_day
                is_full_week_for_end_season = (self.start_date.weekday() == week_start_day and
                                               (self.end_date - self.start_date).days == 7)
            else:
                is_full_week_for_end_season = True if (self.end_date - self.start_date).days == 7 else False
            end_season_filtered_booking_types = end_season_booking_types
            if not is_full_week_for_end_season:
                end_season_filtered_booking_types = end_season_filtered_booking_types.exclude(is_full_week_only=True)
            if not self.is_flexible_period:
                end_season_filtered_booking_types = end_season_filtered_booking_types.exclude(requires_flexible_booking_period=True)
            if not self.is_last_minute_period:
                end_season_filtered_booking_types = end_season_filtered_booking_types.exclude(requires_last_minute_booking_period=True)
            # Validate if there is a compatible booking type in both seasons
            if filtered_booking_types.exists() and end_season_filtered_booking_types.exists():
                self.valid_booking_types = (filtered_booking_types, end_season_filtered_booking_types)
            else:
                self.valid_booking_types = (None, None)
        else:
            if filtered_booking_types.exists():
                self.valid_booking_types = (filtered_booking_types, filtered_booking_types)
            else:
                self.valid_booking_types = (None, None)

    def banned_rooms(self):
        start_types, end_types = self.valid_booking_types
        rooms = self.start_season.config.rooms.all()
        start_banned_rooms = rooms
        end_banned_rooms = rooms
        if start_types and end_types:
            for booking_type in start_types:
                start_banned_rooms = start_banned_rooms & booking_type.banned_rooms.all()
            for booking_type in end_types:
                end_banned_rooms = end_banned_rooms & booking_type.banned_rooms.all()
        return start_banned_rooms.union(end_banned_rooms)


class BookingPage(Page):
    intro = RichTextField(blank=True)
    not_authorised_message = RichTextField(blank=True)
    calendar_text = RichTextField(blank=True, help_text="Text to display above the vacancy calendar")

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("not_authorised_message"),
        FieldPanel("calendar_text")
    ]

    parent_page_types = ['home.HomePage']
    subpage_types = []

    def serve(self, request):
        from corroboree.booking.forms import BookingDateRangeForm, BookingRoomChoosingForm
        if not request.user.is_verified:
            raise PermissionDenied()  # should never happen barring admin shenangians
        else:
            response = refresh_stale_login(request)
            if response:
                return response
        member = request.user.member
        room_form = None
        if member is None:
            return render(request, "booking/not_authorised.html", {
                'page': self,
            })
        else:
            if request.method == "POST":
                room_form = BookingRoomChoosingForm(
                    request.POST,
                    arrival_date=date.fromisoformat(request.POST['arrival_date']),
                    departure_date=date.fromisoformat(request.POST['departure_date']),
                    member=member)
                if room_form.is_valid():
                    # Put the booking in the database as a hold and redirect the user to finish it
                    booking_record = BookingRecord(
                        member=member,
                        member_name_at_creation=member.full_name(),
                        arrival_date=room_form.cleaned_data.get('arrival_date'),
                        departure_date=room_form.cleaned_data.get('departure_date'),
                        member_in_attendance=None,
                        member_in_attendance_name_at_creation='',
                        cost=None,
                        payment_status=BookingRecord.BookingRecordPaymentStatus.NOT_ISSUED,
                        status=BookingRecord.BookingRecordStatus.IN_PROGRESS
                    )
                    booking_record.save()
                    rooms = room_form.cleaned_data.get('room_selection')
                    booking_record.rooms.set(rooms)
                    booking_record.calculate_booking_cart()
                    return redirect('/my-bookings/edit/%s' % booking_record.pk)
                # Preset the date values on the date form for consistency
                arrival_date = room_form.data.get("arrival_date")
                departure_date = room_form.data.get("departure_date")
                date_form = BookingDateRangeForm(initial={
                    "arrival_date": arrival_date,
                    'departure_date': departure_date,
                })
            else:
                date_form = BookingDateRangeForm(request.GET or None)
                if date_form.is_valid():
                    arrival_date = date_form.cleaned_data.get("arrival_date")
                    departure_date = date_form.cleaned_data.get("departure_date")
                    room_form = BookingRoomChoosingForm(arrival_date=arrival_date, departure_date=departure_date, member=member)

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
    edit_guests_text = RichTextField(blank=True,
                                     help_text='Text to display when editing guests')
    pay_text = RichTextField(blank=True,
                             help_text='Text to display at the payment page')
    payment_success_text = RichTextField(blank=True,
                                         help_text='Text to display after a successful payment')
    payment_error_text = RichTextField(blank=True,
                                       help_text='Text to display if the success page is displaying an unpaid booking')
    not_found_text = RichTextField(blank=True,
                                   help_text='Text to display when linked booking is not theirs or editable')
    no_bookings_text = RichTextField(blank=True)
    cancel_text = RichTextField(blank=True,
                                help_text='Text to display above the cancellation form')

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
        MultiFieldPanel(heading='Booking Payment Flow', children=(
            FieldPanel('pay_text'),
            FieldPanel('payment_success_text'),
            FieldPanel('payment_error_text'),
        )),
        MultiFieldPanel(heading='Booking Cancellation Page', children=(
            FieldPanel('cancel_text'),
        )),
    ]

    parent_page_types = ['home.HomePage']
    subpage_types = []

    @path('')
    def booking_index_page(self, request):
        if request.user.is_verified:
            response = refresh_stale_login(request)
            if response:
                return response
            member = request.user.member
            today = date.today()
            bookings = BookingRecord.live_objects.filter(member__exact=member)
            upcoming_bookings = bookings.filter(
                departure_date__gt=today,
                status__exact=BookingRecord.BookingRecordStatus.FINALISED
            ).order_by('arrival_date')
            in_progress_bookings = bookings.filter(
                status__exact=BookingRecord.BookingRecordStatus.IN_PROGRESS
            ).order_by('arrival_date')
            submitted_bookings = bookings.filter(
                status__exact=BookingRecord.BookingRecordStatus.SUBMITTED
            ).order_by('arrival_date')
            return self.render(request, context_overrides={
                'title': 'My Bookings',
                'upcoming_bookings': upcoming_bookings,
                'in_progress_bookings': in_progress_bookings,
                'submitted_bookings': submitted_bookings,
            })

    @path('edit/<int:booking_id>/')
    def booking_edit_page(self, request, booking_id=None):
        from corroboree.booking.forms import BookingRecordMemberInAttendanceForm, GuestForm
        if request.user.is_verified:
            response = refresh_stale_login(request)
            if response:
                return response
            member = request.user.member
            if booking_id is None:
                booking_id = BookingRecord.live_objects.filter(member=member).order_by('last_updated').first()
            # Try to find the booking, but make sure it's ours and editable!
            try:
                booking = BookingRecord.live_objects.get(
                    pk=booking_id,
                    member=member,
                )
            except BookingRecord.DoesNotExist:  # Due to using PK no need to catch multiple objects
                booking = None
                return self.render(request, template='booking/booking_not_found.html')
            # make a form
            if booking.status != BookingRecord.BookingRecordStatus.FINALISED:
                member_in_attendance_form = BookingRecordMemberInAttendanceForm(member=member,
                                                                                member_in_attendance=booking.member_in_attendance)
            else:
                member_in_attendance_form = None
            max_attendees = booking.rooms.aggregate(max_occupants=Sum('room_type__max_occupants'))['max_occupants']
            GuestFormSet = formset_factory(GuestForm, extra=max_attendees - 1, max_num=max_attendees - 1)
            if request.method == 'POST':  # User has submitted the guest form
                guest_forms = GuestFormSet(request.POST)
                # We won't update the member in attendance for finalised bookings
                if booking.status != BookingRecord.BookingRecordStatus.FINALISED:
                    member_in_attendance_form = BookingRecordMemberInAttendanceForm(request.POST)
                    if member_in_attendance_form.is_valid():
                        member_in_attendance = member_in_attendance_form.cleaned_data['member_in_attendance']
                        booking.member_in_attendance = member_in_attendance
                        booking.member_in_attendance_name_at_creation = member_in_attendance.full_name()
                if guest_forms.is_valid():
                    guests = {}
                    for idguest, guest in enumerate(guest_forms):
                        guests['guest_%s' % idguest] = {
                            'first_name': guest.cleaned_data.get('first_name', ''),
                            'last_name': guest.cleaned_data.get('last_name', ''),
                            'email': guest.cleaned_data.get('email', ''),
                        }
                    other_attendees = guests
                    booking.other_attendees = other_attendees
                    booking.save()
                    # Redirect users who need to pay to payment
                    if booking.status == BookingRecord.BookingRecordStatus.IN_PROGRESS or booking.status == BookingRecord.BookingRecordStatus.SUBMITTED:
                        booking.status = booking.update_status(BookingRecord.BookingRecordStatus.SUBMITTED)
                        return redirect(self.url + 'pay/%s' % booking_id)
                    else:  # Booking is already submitted or finalised
                        booking.send_related_email(
                            subject='Neige Booking Updated: {start} - {end}'.format(
                                start=booking.arrival_date,
                                end=booking.departure_date
                            ),
                            email_text='The guest list has been updated:'
                        )
                        return redirect(self.url)
            else:
                attendees = list(booking.other_attendees.values())
                guest_forms = GuestFormSet(initial=attendees)
            return self.render(request,
                               context_overrides={
                                   'title': 'Edit Booking',
                                   'booking': booking,
                                   'booking_cart': booking.explain_booking_cart(),
                                   'member_in_attendance_form': member_in_attendance_form,
                                   'guest_forms': guest_forms,
                               },
                               template='booking/edit_booking.html',
                               )

    @path('pay/<int:booking_id>/')
    def booking_payment_page(self, request, booking_id=None):
        if request.user.is_verified:
            response = refresh_stale_login(request)
            if response:
                return response
            member = request.user.member
            if booking_id is None:
                booking_id = BookingRecord.live_objects.filter(member=member).order_by('last_updated').first()
            try:
                booking = BookingRecord.live_objects.get(
                    pk=booking_id,
                    member=member,
                    status=BookingRecord.BookingRecordStatus.SUBMITTED,
                    payment_status=BookingRecord.BookingRecordPaymentStatus.NOT_ISSUED,  # Maybe need failed? if
                    # that's even needed
                )
            except BookingRecord.DoesNotExist:  # Due to using PK no need to catch multiple objects
                return self.render(request,
                                   template='booking/booking_not_found.html')  # TODO: Mod template for url message
            return self.render(request,
                               context_overrides={
                                   'title': 'Confirm and Pay',
                                   'booking': booking,
                               },
                               template='booking/pay_booking.html',
                               )

    @path('pay/success/')
    def booking_thanks_page(self, request):
        booking_id = request.GET.get('booking')
        if request.user.is_verified:
            member = request.user.member
            if not booking_id:
                raise Http404("Booking ID not provided")
            try:
                booking = BookingRecord.live_objects.get(
                    pk=booking_id,
                    member=member,
                )
            except BookingRecord.DoesNotExist:
                return self.render(request,
                                   template='booking/booking_not_found.html')
            paid = False
            if booking.status == BookingRecord.BookingRecordStatus.FINALISED and booking.payment_status == BookingRecord.BookingRecordPaymentStatus.PAID:
                paid = True
            return self.render(request,
                               context_overrides={
                                   'title': 'Thanks for Paying',
                                   'booking': booking,
                                   'paid': paid,
                               },
                               template='booking/booking_thanks.html',
                               )

    @path('cancel/<int:booking_id>/')
    def booking_delete_page(self, request, booking_id=None):
        if request.user.is_verified:
            response = refresh_stale_login(request)
            if response:
                return response
            member = request.user.member
            if booking_id is None:
                booking_id = BookingRecord.live_objects.filter(member=member).order_by('last_updated').first()
            # Try to find the booking, but make sure it's ours and editable!
            try:
                booking = BookingRecord.live_objects.get(
                    pk=booking_id,
                    member=member,
                    status__in=[
                        BookingRecord.BookingRecordStatus.IN_PROGRESS,
                        BookingRecord.BookingRecordStatus.SUBMITTED,
                    ]
                )
            except BookingRecord.DoesNotExist:  # Due to using PK no need to catch multiple objects
                booking = None
                return self.render(request, template='booking/booking_not_found.html')
            if request.method == 'POST':
                booking.update_status(BookingRecord.BookingRecordStatus.CANCELLED)
                return redirect(self.url)
            else:
                return self.render(request,
                                   context_overrides={
                                       'title': 'Confirm Cancellation',
                                       'booking': booking,
                                   },
                                   template='booking/cancel_booking.html',
                                   )


class BookingCalendar(Page):
    caption = RichTextField(blank=True, help_text='Displays under the calendar')
    content_panels = Page.content_panels + [
        FieldPanel('caption')
    ]

    parent_page_types = ['home.HomePage']
    subpage_types = []


def refresh_stale_login(request, td=timedelta(days=1)):
    """Check if the session is older than 24 hours. If it is prompt the user to reauthenticate
    
    Redirect must be called in serve method, so something like if not none return (result)"""
    login_age = timezone.now() - request.user.last_login
    if login_age > td:
        messages.add_message(request, messages.INFO, 'Please reauthenticate in order to use the booking functions.')
        return redirect('login')
    else:
        return None


def bookings_for_member_in_range(member: config.Member, arrival_date: date, departure_date: date):
    """Given a member and a date range returns bookings for that member within that date range (including partially)"""
    bookings = member.bookings(manager='live_objects').exclude(departure_date__lte=arrival_date).exclude(
        arrival_date__gte=departure_date)
    return bookings

def create_booking_cart_periods(start_date: date, end_date: date) -> [BookingCartPeriod]:
    # Info relating to classifying periods
    conf = config.Config.objects.get()
    week_start_day = conf.week_start_day
    tod_rollover = conf.time_of_day_rollover
    last_minute_weeks = conf.last_minute_booking_weeks + 1  # idiosyncratic ski club rules
    flexible_booking_weeks = conf.flexible_booking_weeks + 1 # idiosyncratic ski club rules
    aest_now = datetime.now(pytz.timezone('Australia/Sydney'))
    compare_date = aest_now.date() if aest_now.time() >= tod_rollover else aest_now.date() - timedelta(days=1)
    last_week_start = last_weekday_date(compare_date, week_start_day)
    # And finally
    last_minute_period_end = compare_date + timedelta(weeks=last_minute_weeks)
    flexible_period_end = last_week_start + timedelta(weeks=flexible_booking_weeks)
    # Start making booking periods
    booking_cart_periods = []
    seasons = conf.seasons_in_date_range(start_date, end_date)
    current_date = start_date
    while current_date < end_date:
        start_season = seasons_to_season_on_day(seasons, current_date)
        # The end of the period depends on strict weeks behaviour
        if current_date + timedelta(weeks=1) <= last_minute_period_end:
            # last minute bookings enforce relaxed weeks
            end_period_date = current_date + timedelta(weeks=1)
        elif start_season.requires_strict_weeks:
            end_period_date = last_weekday_date(current_date, week_start_day) + timedelta(weeks=1)
        else:
            end_period_date = current_date + timedelta(weeks=1)
        # Patch an overshoot
        if end_period_date > end_date:
            end_period_date = end_date
        # period properties
        is_full_week = (end_period_date - current_date).days == 7
        is_flexible_period = end_period_date <= flexible_period_end
        is_last_minute_period = end_period_date <= last_minute_period_end
        if end_period_date.month != current_date.month:
            end_season = seasons_to_season_on_day(seasons, end_period_date)
        else:
            end_season = start_season
        booking_cart_period = BookingCartPeriod(
            start_date=current_date,
            end_date=end_period_date,
            start_season=start_season,
            end_season=end_season,
            is_full_week=is_full_week,
            is_flexible_period=is_flexible_period,
            is_last_minute_period=is_last_minute_period
        )
        booking_cart_periods.append(booking_cart_period)
        current_date = end_period_date
    return booking_cart_periods




def dates_to_weeks(arrival_date: date, departure_date: date, week_start_day=5) -> (int, int, int):
    """For a date range and day of week return the number of weeks and surrounding 'spare' days

    Using datetime weekday ints monday=0 sunday=6.
    """
    total_days = (departure_date - arrival_date).days
    start_weekday = arrival_date.weekday()
    end_weekday = departure_date.weekday()
    leading_days = (week_start_day - start_weekday) % 7
    if total_days <= leading_days:
        return total_days, 0, 0
    else:
        trailing_days = (7 - (week_start_day - end_weekday)) % 7
        from_week = arrival_date + timedelta(days=leading_days)
        till_week = departure_date - timedelta(days=trailing_days)
        weeks = int((till_week - from_week).days / 7)
        return leading_days, weeks, trailing_days


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


def check_season_rules(member: config.Member, arrival_date: datetime.date, departure_date: datetime.date, rooms: [config.Room]):
    """ Given a member, a range of dates, and the rooms they would like to book for those dates. Validates the season rules which apply"""
    conf = config.Config.objects.get()  # only valid for single config
    if member.share_number == 0:
        # Maintenance booking, allow anything
        return
    elif departure_date <= date.today() + timedelta(weeks=conf.last_minute_booking_weeks):
        # Assuming the end date is already otherwise valid you can book anything 2 weeks out
        return
    for start, end in date_range_to_month_ranges(arrival_date, departure_date):
        room_start, room_end = daterange_of_a_in_b(arrival_date, departure_date, start, end)
        overlapping_bookings = bookings_for_member_in_range(member, start, end)
        occupancy_array = room_occupancy_array(start, end, rooms, room_start, room_end, overlapping_bookings)
        season_in_month = conf.seasons_in_date_range(start, end)
        # account for peak seasons
        if season_in_month.count() == 1:
            season_in_month = season_in_month.first()
        else:
            season_in_month = season_in_month.filter(season_is_peak=True).first()
        sum_rooms = []
        for day in range(0, len(occupancy_array[0])):
            sum_rooms.append(sum([booked_rooms[day] for booked_rooms in occupancy_array]))
            if season_in_month.max_monthly_room_weeks is not None:
                if sum(sum_rooms) / 7 > season_in_month.max_monthly_room_weeks:
                    raise ValidationError(
                        'This booking exceeds the {max} room-weeks limit for {season} during {month}'.format(
                            max=season_in_month.max_monthly_room_weeks,
                            season=season_in_month.season_name,
                            month=start.strftime('%B')
                        )
                    )


def date_range_to_month_ranges(start: datetime.date, end: datetime.date) -> [(datetime.date, datetime.date)]:
    """Splits a start and end date into ranges by month

    Used for checking season rules"""
    start = start.replace(day=1)
    end = last_day_of_month(end)
    result = []
    while True:
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1, day=1)
        else:
            next_month = start.replace(month=start.month + 1, day=1)
        if next_month > end:
            break
        result.append((start, last_day_of_month(start)))
        start = next_month
    result.append((start, end))
    return result


def daterange_of_a_in_b(a_start: date, a_end: date, b_start: date, b_end: date) -> (date, date):
    """Returns the subset of the range a which is in range b"""
    overlap_start = max(a_start, b_start)
    overlap_end = min(a_end, b_end)
    return overlap_start, overlap_end

def last_day_of_month(day: datetime.date):
    next_month = day.replace(day=28) + timedelta(days=4)
    return next_month - timedelta(days=next_month.day)


def room_occupancy_array(start: date, end: date, rooms: [config.Room], room_start: date, room_end: date,
                         other_bookings: [BookingRecord]):
    """create a list of lists where the inner lists represent the number of rooms booked by that booking on that day"""
    # on reflection this might be overkill and could probably just be a list of the sum of rooms booked on that day?
    # TODO: length = (end - start).days is 1 day short of the full month, the last day of room_start -> end isn't 'occupied' but more nuance is needed to handle the difference between the booking ending or continuing past the month
    array = []
    length = (end - start).days + 1
    start_delta = max(0, (room_start - start).days)
    end_delta = max(0, (end - room_end).days + 1)  # last day is not occupied
    array.append([0] * start_delta + [len(rooms)] * (length - (start_delta + end_delta)) + [0] * end_delta)
    for this_booking in other_bookings:
        num_rooms = this_booking.rooms.all().count()
        # pad a list with the days vacant at start or end, so we know the rooms on each day
        start_delta = max(0, (this_booking.arrival_date - start).days)
        end_delta = max(0, (end - this_booking.departure_date).days + 1) # last day is not occupied
        array.append([0] * start_delta + [num_rooms] * (length - (start_delta + end_delta)) + [0] * end_delta)
    return array


def booked_rooms(arrival_date, departure_date) -> [int]:
    """Returns a flat list of room numbers currently booked between dates"""
    current_booking_records = BookingRecord.live_objects.filter(
        departure_date__gt=date.today(),
        arrival_date__lt=departure_date,
    )
    overlapping_bookings = current_booking_records.exclude(
        arrival_date__gte=departure_date).exclude(
        departure_date__lte=arrival_date,
    )
    booked_room_ids = overlapping_bookings.values_list('rooms__room_number', flat=True)
    return booked_room_ids


def last_weekday_date(date: date, weekday=5):
    """Given a date and weekday, return the date of the last weekday (datetime ints [0-6])"""
    date_day = date.weekday()
    delta = timedelta((7 - (weekday - date_day)) % 7)
    return date - delta
