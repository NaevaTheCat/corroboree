import datetime
from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError, PermissionDenied
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.db import models
from django.db.models import Sum, Q
from django_filters import FilterSet, ModelMultipleChoiceFilter, CharFilter, DateFilter, ChoiceFilter
from django.forms import formset_factory, CheckboxSelectMultiple
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_protect
from django.http import Http404, HttpResponseServerError
from wagtail.admin.panels import FieldPanel, FieldRowPanel, MultiFieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.admin.widgets import AdminDateInput
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from corroboree.config import models as config


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
    start_date = models.DateField()
    end_date = models.DateField()
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

    objects = models.Manager()
    live_objects = LiveBookingRecordManager()

    def __str__(self):
        return '[{id}] {start} - {end}: {member}'.format(
            id=self.pk,
            start=self.start_date,
            end=self.end_date,
            member=self.member,
        )

    def rooms_list(self):
        rooms = list(self.rooms.all())
        return ', '.join(str(r) for r in rooms)

    def calculate_booking_cart(self, conf: config.Config):
        booking_types = get_booking_types(conf, self.start_date, self.end_date)
        cost = 0
        for day in booking_types:
            # add the cost of the highest (smallest int) priority booking mult by rooms
            booking_type = booking_types[day].exclude(
                banned_rooms__in=self.rooms.all()).exclude(
                minimum_rooms__gt=self.rooms.count()).order_by(
                'priority_rank').first()
            if booking_type.is_flat_rate:
                cost += booking_type.rate
            else:
                cost += self.rooms.count() * booking_type.rate
        self.cost = cost
        self.save()

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


class BookingRecordFilter(FilterSet):
    rooms = ModelMultipleChoiceFilter(
        queryset=config.Room.objects.all(),
        widget=CheckboxSelectMultiple,
        label='Rooms',
        method='filter_rooms',
    )
    member_last_name = CharFilter(field_name='member__last_name', lookup_expr='iexact', label='Member Last Name')
    member_first_name = CharFilter(field_name='member__first_name', lookup_expr='iexact', label='Member First Name')
    member_in_attendance_last_name = CharFilter(field_name='member_in_attendance__last_name', lookup_expr='iexact',
                                                label='Member in Attendance Last Name')
    member_in_attendance_first_name = CharFilter(field_name='member_in_attendance__first_name', lookup_expr='iexact',
                                                 label='Member in Attendance First Name')
    start_date_lt = DateFilter(field_name='start_date', lookup_expr='lt', label='Start Date Before', widget=AdminDateInput)
    start_date_gt = DateFilter(field_name='start_date', lookup_expr='gt', label='Start Date After', widget=AdminDateInput)
    end_date_lt = DateFilter(field_name='end_date', lookup_expr='lt', label='End Date Before', widget=AdminDateInput)
    end_date_gt = DateFilter(field_name='end_date', lookup_expr='gt', label='End Date After', widget=AdminDateInput)
    status = ChoiceFilter(field_name='status', lookup_expr='exact', label='Status', choices=BookingRecord.BookingRecordStatus)
    payment_status = ChoiceFilter(field_name='payment_status', lookup_expr='iexact', label='Payment Status', choices=BookingRecord.BookingRecordPaymentStatus)
    paypal_transaction_id = CharFilter(field_name='paypal_transaction_id', lookup_expr='exact', label='PayPal Transaction ID')
    cost_lt = CharFilter(field_name='cost', lookup_expr='lt', label='Cost Less Than')
    cost_gt = CharFilter(field_name='cost', lookup_expr='gt', label='Cost Greater Than')

    class Meta:
        model = BookingRecord
        fields = [
            'member_last_name',
            'member_first_name',
            'member_in_attendance_last_name',
            'member_in_attendance_first_name',
            'start_date_lt',
            'start_date_gt',
            'end_date_lt',
            'end_date_gt',
            'rooms',
        ]

    def filter_rooms(self, queryset, name, value):
        for room in value:
            queryset = queryset.filter(rooms=room)
        return queryset


class BookingRecordViewSet(SnippetViewSet):
    model = BookingRecord
    icon = 'form'
    menu_label = 'Bookings'
    menu_name = 'bookings'
    menu_order = 300
    add_to_admin_menu = True
    list_display = [
        'member',
        'start_date',
        'end_date',
        'member_in_attendance',
        'status',
        'payment_status',
        'cost',
        'paypal_transaction_id',
        'rooms_list',
    ]
    list_export = [
        'member',
        'member_name_at_creation',
        'last_updated',
        'start_date',
        'end_date',
        'member_in_attendance',
        'member_in_attendance_name_at_creation',
        'other_attendees',
        'status',
        'payment_status',
        'cost',
        'paypal_transaction_id',
        'rooms_list',
    ]
    list_per_page = 50
    copy_view_enabled = False
    inspect_view_enabled = True
    admin_url_namespace = 'bookings_view'
    base_url_path = 'internal/bookings'
    filterset_class = BookingRecordFilter

    panels = [
        FieldRowPanel([
            FieldPanel('member'),
            FieldPanel('member_name_at_creation')
        ]),
        FieldRowPanel([
            FieldPanel('member_in_attendance'),
            FieldPanel('member_in_attendance_name_at_creation')
        ]),
        FieldRowPanel([
            FieldPanel('start_date'),
            FieldPanel('end_date'),
        ]),
        FieldPanel('rooms', widget=CheckboxSelectMultiple),
        FieldPanel('other_attendees'),
        FieldPanel('cost'),
        FieldRowPanel([
            FieldPanel('status'),
            FieldPanel('payment_status'),
            FieldPanel('paypal_transaction_id'),
        ]),
    ]


register_snippet(BookingRecordViewSet)


class BookingPage(Page):
    intro = RichTextField(blank=True)
    not_authorised_message = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("not_authorised_message")
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
                    start_date=date.fromisoformat(request.POST['start_date']),
                    end_date=date.fromisoformat(request.POST['end_date']),
                    member=member)
                if room_form.is_valid():
                    # Put the booking in the database as a hold and redirect the user to finish it
                    booking_record = BookingRecord(
                        member=member,
                        member_name_at_creation=member.full_name(),
                        start_date=room_form.cleaned_data.get('start_date'),
                        end_date=room_form.cleaned_data.get('end_date'),
                        member_in_attendance=None,
                        member_in_attendance_name_at_creation='',
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
            else:
                date_form = BookingDateRangeForm(request.GET or None)
                if date_form.is_valid():
                    start_date = date_form.cleaned_data.get("start_date")
                    end_date = date_form.cleaned_data.get("end_date")
                    room_form = BookingRoomChoosingForm(start_date=start_date, end_date=end_date, member=member)

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
        if request.user.is_verified:
            response = refresh_stale_login(request)
            if response:
                return response
            member = request.user.member
            if booking_id is None:
                booking_id = BookingRecord.live_objects.filter(member=member).order_by('last_updated').first()
            # Try find the booking, but make sure it's ours and editable!
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
                member_in_attendance_form = BookingRecordMemberInAttendanceForm(member=member, member_in_attendance=booking.member_in_attendance)
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
                                start=booking.start_date,
                                end=booking.end_date
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
                booking = None
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
            # Try find the booking, but make sure it's ours and editable!
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
    content_panels = Page.content_panels

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


def bookings_for_member_in_range(member: config.Member, start_date: date, end_date: date):
    """Given a member and a date range returns bookings for that member within that date range (including partially)"""
    bookings = member.bookings(manager='live_objects').exclude(end_date__lte=start_date).exclude(start_date__gte=end_date)
    return bookings


def dates_to_weeks(start_date: date, end_date: date, week_start_day=5) -> (int, int, int):
    """For a date range and day of week return the number of weeks and surrounding 'spare' days

    Using datetime weekday ints monday=0 sunday=6.
    """
    total_days = (end_date - start_date).days
    start_weekday = start_date.weekday()
    end_weekday = end_date.weekday()
    leading_days = (week_start_day - start_weekday) % 7
    if total_days <= leading_days:
        return total_days, 0, 0
    else:
        trailing_days = (7 - (week_start_day - end_weekday)) % 7
        from_week = start_date + timedelta(days=leading_days)
        till_week = end_date - timedelta(days=trailing_days)
        weeks = int((till_week - from_week).days / 7)
        return leading_days, weeks, trailing_days


def get_booking_types(conf: config.Config, start_date: date, end_date: date):
    """Returns a dictionary of date-keyed booking type querysets with dates matching either a week start or a 'spare' day

    Assumes that a week has a weekly booking type. Will not return daily bookings for week-equivalent dates"""
    leading_days, weeks, trailing_days = dates_to_weeks(start_date, end_date, week_start_day=conf.week_start_day)
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


def check_season_rules(member: config.Member, start_date: datetime.date, end_date: datetime.date, rooms: [config.Room]):
    """ Given a member, a range of dates, and the rooms they would like to book for those dates. Validates the season rules which apply"""
    conf = config.Config.objects.get()  # only valid for single config
    if member.share_number == 0:
        # Maintenance booking, allow anything
        return
    elif end_date <= date.today() + timedelta(weeks=conf.last_minute_booking_weeks):
        # Assuming the end date is already otherwise valid you can book anything 2 weeks out
        return
    for start, end in date_range_to_month_ranges(start_date, end_date):
        overlapping_bookings = bookings_for_member_in_range(member, start, end)
        occupancy_array = room_occupancy_array(start, end, rooms, overlapping_bookings)
        season_in_month = conf.seasons_in_date_range(start, end)
        # account for peak seasons
        if season_in_month.count() == 1:
            season_in_month = season_in_month.first()
        else:
            season_in_month = season_in_month.filter(season_is_peak=True).first()
        sum_rooms = []
        for day in range(0, len(occupancy_array[0])):
            sum_rooms.append(sum([booked_rooms[day] for booked_rooms in occupancy_array]))
            if season_in_month.max_monthly_simultaneous_rooms is not None:
                # test the number of max rooms
                if max(sum_rooms) > season_in_month.max_monthly_simultaneous_rooms:
                    raise ValidationError(
                        'This booking exceeds the {max} simultaneous rooms limit for {season} on {date}'.format(
                            max=season_in_month.max_monthly_simultaneous_rooms,
                            season=season_in_month.season_name,
                            date=start_date + timedelta(days=sum_rooms.index(max(sum_rooms))),
                        )
                    )
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


def last_day_of_month(day: datetime.date):
    next_month = day.replace(day=28) + timedelta(days=4)
    return next_month - timedelta(days=next_month.day)


def room_occupancy_array(start_date: datetime.date, end_date: datetime.date, rooms: [config.Room],
                         other_bookings: [BookingRecord]):
    """create a list of lists where the inner lists represent the number of rooms booked by that booking on that day"""
    # on reflection this might be overkill and could probably just be a list of the sum of rooms booked on that day?
    array = []
    length = (end_date - start_date).days
    array.append([len(rooms)] * length)
    for this_booking in other_bookings:
        num_rooms = this_booking.rooms.all().count()
        # pad a list with the days vacant at start or end, so we know the rooms on each day
        start_delta = max(0, (this_booking.start_date - start_date).days)
        end_delta = max(0, (end_date - this_booking.end_date).days)
        array.append([0] * start_delta + [num_rooms] * (length - (start_delta + end_delta)) + [0] * end_delta)
    return array


def booked_rooms(start_date, end_date) -> [int]:
    """Returns a flat list of room numbers currently booked between dates"""
    current_booking_records = BookingRecord.live_objects.filter(
        end_date__gt=date.today(),
        start_date__lt=end_date,
    )
    overlapping_bookings = current_booking_records.exclude(
        start_date__gte=end_date).exclude(
        end_date__lte=start_date,
    )
    booked_room_ids = overlapping_bookings.values_list('rooms__room_number', flat=True)
    return booked_room_ids
