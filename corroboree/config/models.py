import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, MinLengthValidator, MaxLengthValidator
from django.db import models
from django.db.models import F, Q
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel


# Validators
def validate_only_one_instance(obj):
    model = obj.__class__
    if (model.objects.count() > 0 and
            obj.pk != model.objects.get().pk):
        raise ValidationError("Can only create 1 %s instance" % model.__name__)


class Config(ClusterableModel):
    class Weekday(models.IntegerChoices):
        Monday = 0
        Tuesday = 1
        Wednesday = 2
        Thursday = 3
        Friday = 4
        Saturday = 5
        Sunday = 6
    max_weeks_till_booking = models.IntegerField(default=26)
    time_of_day_rollover = models.TimeField(
        help_text="What time of day to open bookings for the day max_weeks_till_booking from now")
    number_of_rooms = models.IntegerField(default=9)
    week_start_day = models.IntegerField(choices=Weekday,
                                         help_text="The day used to determine when a week starts")
    last_minute_booking_weeks = models.IntegerField(default=2,
                                                    help_text="Number of weeks for last minute booking rules to apply")
    maximum_family_members = models.IntegerField(
        default=10,
        help_text="maximum authorised family members including primary shareholder"
    )

    panels = [
        FieldPanel("week_start_day"),
        FieldRowPanel([
            FieldPanel("max_weeks_till_booking"),
            FieldPanel("last_minute_booking_weeks"),
            FieldPanel("time_of_day_rollover"),
        ]),
        FieldPanel("maximum_family_members"),
        InlinePanel("members", label="Members",
                    panels=[
                        FieldPanel("config"),
                        FieldPanel("share_number"),
                        FieldRowPanel([
                            FieldPanel("first_name"),
                            FieldPanel("last_name"),
                        ]),
                        FieldPanel("contact_email"),
                    ]),
        FieldPanel("number_of_rooms"),
        InlinePanel("room_types", label="Room Types",
                    panels=[
                        FieldRowPanel([
                            FieldPanel("double_beds"),
                            FieldPanel("bunk_beds"),
                        ]),
                    ]),
        InlinePanel('seasons', label='Seasons'),
    ]

    def seasons_in_date_range(self, start_date: datetime.date, end_date: datetime.date):
        """Returns a Queryset of seasons that are active during any part of a date range"""
        start_month = start_date.month
        end_month = end_date.month
        # given months can wrap need to capture the 4 cases of comparison
        if start_month <= end_month:
            seasons = self.seasons.exclude(
                Q(start_month__lte=F('end_month')) & (Q(start_month__gt=end_month) | Q(end_month__lt=start_month))
            ).exclude(
                Q(start_month__gt=F('end_month')) & (Q(end_month__lt=start_month) & Q(start_month__gt=end_month))
            )
        else:
            seasons = self.seasons.exclude(
                Q(start_month__lte=F('end_month')) & (Q(start_month__gt=end_month) & Q(end_month__lt=start_month))
            )
        return seasons

    def clean(self):
        validate_only_one_instance(self)


class PersonBase(models.Model):
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=10, validators=[MinLengthValidator(10)])

    common_panels = [
        FieldRowPanel([
            FieldPanel("first_name"),
            FieldPanel("last_name"),
        ]),
        FieldRowPanel([
            FieldPanel("contact_email"),
            FieldPanel("contact_phone")
        ]),
    ]

    class Meta:
        abstract = True

    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name()


class Member(PersonBase, ClusterableModel):
    config = ParentalKey(Config, on_delete=models.PROTECT, related_name="members")
    share_number = models.IntegerField(primary_key=True,
                                       validators=[
                                           MaxValueValidator(50, message="Cannot exceed 50 shares"),
                                           MinValueValidator(0, message="Share number is less than 1")
                                       ])

    panels = [
        FieldPanel("config"),
        FieldPanel("share_number"),
        ] + PersonBase.common_panels + [
        InlinePanel("family", label="Family", help_text="Include the share owner"),
    ]

    def __str__(self):
        share_prefix = '[' + str(self.share_number) + ']: '
        return share_prefix + self.full_name()


class FamilyMember(PersonBase, ClusterableModel):
    primary_shareholder = ParentalKey(Member, on_delete=models.CASCADE, related_name="family")

    panels = [
        FieldPanel("primary_shareholder"),
    ] + PersonBase.common_panels

    def __str__(self):
        share_holder = '(' + str(self.primary_shareholder) + ') '
        return share_holder + self.full_name()

    def clean(self):
        if not hasattr(self, 'primary_shareholder'):
            return
        maximum_family_members = self.primary_shareholder.config.maximum_family_members
        if self.primary_shareholder.family.exclude(pk=self.pk).count() >= maximum_family_members:
            raise ValidationError("Cannot add more than %s family members" % str(maximum_family_members))


class RoomType(ClusterableModel):
    config = ParentalKey(Config, on_delete=models.CASCADE, related_name="room_types")
    # TODO move to limits to settings
    double_beds = models.IntegerField(validators=[
        MaxValueValidator(2),
        MinValueValidator(0),
    ])
    bunk_beds = models.IntegerField(validators=[
        MaxValueValidator(4),
        MinValueValidator(0),
    ])
    max_occupants = models.GeneratedField(
        expression=F("double_beds") * 2 + F("bunk_beds"),
        output_field=models.IntegerField(),
        db_persist=True)

    panels = [
        FieldRowPanel([
            FieldPanel("double_beds"),
            FieldPanel("bunk_beds"),
        ]),
        InlinePanel("rooms", label="Rooms of Type"),
    ]

    def __str__(self):  # bad plurals
        double_text = "" if self.double_beds == 0 else str(self.double_beds) + " double bed"
        bunk_text = "" if self.bunk_beds == 0 else str(self.bunk_beds) + " bunk beds"
        if bunk_text == "" or double_text == "":
            join_text = ""
        else:
            join_text = ", "
        return double_text + join_text + bunk_text


class Room(ClusterableModel):
    # TODO validators to settings
    config = ParentalKey(Config, on_delete=models.PROTECT, related_name="rooms")
    room_number = models.IntegerField(primary_key=True, validators=[
        MaxValueValidator(9, "Exceeds maximum rooms"),
        MinValueValidator(1),
    ])
    room_type = ParentalKey(RoomType, on_delete=models.PROTECT, related_name="rooms")

    def __str__(self):
        return str(self.room_number) + ': ' + str(self.room_type)


class Season(ClusterableModel):
    config = ParentalKey(Config, on_delete=models.PROTECT, related_name="seasons")

    class Months(models.IntegerChoices):
        January = 1
        February = 2
        March = 3
        April = 4
        May = 5
        June = 6
        July = 7
        August = 8
        September = 9
        October = 10
        November = 11
        December = 12

    season_name = models.CharField(max_length=128)
    max_monthly_room_weeks = models.IntegerField(blank=True, null=True,
                                                 help_text="Leave blank for no limit")
    max_monthly_simultaneous_rooms = models.IntegerField(blank=True, null=True,
                                                         help_text="Leave blank for no limit")
    start_month = models.IntegerField(choices=Months,
                                      help_text="The season will begin at the first day of the selected month")
    end_month = models.IntegerField(choices=Months,
                                    help_text="The season will end at the end of the last day of the selected month")
    season_is_peak = models.BooleanField()

    panels = [
        FieldPanel("config"),
        FieldPanel("season_name"),
        FieldRowPanel([
            FieldPanel('max_monthly_simultaneous_rooms'),
            FieldPanel("max_monthly_room_weeks"),
        ]),
        FieldRowPanel([
            FieldPanel("start_month"),
            FieldPanel("end_month"),
        ]),
        FieldPanel("season_is_peak"),
    ]

    def __str__(self):
        return self.season_name

    def date_is_in_season(self, date: datetime.date) -> bool:
        month = date.month
        if self.start_month <= self.end_month:
            return True if self.start_month <= month <= self.end_month else False
        else:
            return True if self.start_month <= month or month <= self.end_month else False

    def clean(self):
        # make sure correct stuff is set
        if not hasattr(self, 'config') or self.start_month is None or self.end_month is None:
            return
        # compare like-kinded seasons
        if self.season_is_peak:
            other_seasons = self.config.seasons.filter(season_is_peak=True).exclude(pk=self.pk)
        else:
            other_seasons = self.config.seasons.filter(season_is_peak=False).exclude(pk=self.pk)
        this_start = self.start_month
        this_end = self.end_month
        # need to test the 4 permutations of whether seasons wrap around the year easy to test not overlap
        if this_end >= this_start:
            for s in other_seasons:
                if s.end_month >= s.start_month:
                    if not (this_end < s.start_month or s.end_month < this_start):
                        raise ValidationError("This season shares months with %s" % s)
                else:
                    if not (this_start > s.end_month or this_end < s.start_month):
                        raise ValidationError("This season shares months with %s" % s)
        else:
            for s in other_seasons:
                if s.end_month >= s.start_month:
                    if not (this_end < s.start_month and this_start > s.end_month):
                        raise ValidationError("This season shares months with %s" % s)
                else:
                    raise ValidationError("This season shares months with %s" % s)


class BookingType(ClusterableModel):
    config = ParentalKey(Config, on_delete=models.PROTECT, related_name="booking_types")
    booking_type_name = models.CharField(max_length=128)
    rate = models.DecimalField(max_digits=8, decimal_places=2)
    is_full_week_only = models.BooleanField(default=False)
    is_flat_rate = models.BooleanField(
        default=False,
        help_text='If set, the fee for this booking is not multiplied by the number of rooms booked')
    banned_rooms = ParentalManyToManyField(Room, blank=True)
    season_active = ParentalKey(Season, on_delete=models.CASCADE, related_name="booking_types")
    minimum_rooms = models.IntegerField("Minimum number of booked rooms", default=0)

    class Priorities(models.IntegerChoices):
        HIGH = 1
        MEDIUM = 2
        LOW = 3

    priority_rank = models.IntegerField(choices=Priorities, default=Priorities.LOW,
                                        help_text="Priority booking takes when calculating costs when multiple kinds are valid.")

    panels = [
        FieldPanel("config"),
        FieldPanel("booking_type_name"),
        FieldRowPanel([
            FieldPanel("season_active"),
            FieldPanel("rate"),
            FieldPanel("is_full_week_only"),
            FieldPanel('is_flat_rate'),
        ]),
        FieldPanel("banned_rooms", widget=forms.CheckboxSelectMultiple),
        FieldPanel("minimum_rooms"),
        FieldPanel("priority_rank"),
    ]

    def __str__(self):
        return self.booking_type_name

    def clean(self):
        if not hasattr(self, 'config') or not hasattr(self, 'season_active'):
            return
        # ensure unique priorities
        similar_priority_bookings = self.season_active.booking_types.filter(priority_rank=self.priority_rank).exclude(
            pk=self.pk
        )
        if similar_priority_bookings.count() > 0:
            raise ValidationError(
                "Overlapping priority with BookingType: %s" % similar_priority_bookings.get().booking_type_name)
