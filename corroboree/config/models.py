from django.db import models
from django.db.models import F
from django import forms

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from wagtail.admin.panels import FieldPanel, FieldRowPanel
from wagtail.snippets.models import register_snippet


# Validators
def validate_only_one_instance(obj):
    model = obj.__class__
    if (model.objects.count() > 0 and
            obj.pk != model.objects.get().pk):
        raise ValidationError("Can only create 1 %s instance" % model.__name__)


@register_snippet
class Config(models.Model):
    max_weeks_till_booking = models.IntegerField(default=26)
    time_of_day_rollover = models.TimeField(
        help_text="What time of day to open bookings for the day max_weeks_till_booking from now")

    def clean(self):
        validate_only_one_instance(self)


@register_snippet
class Member(models.Model):
    config = models.ForeignKey(Config, on_delete=models.PROTECT)
    share_number = models.IntegerField(primary_key=True,
                                       validators=[
                                           MaxValueValidator(50, message="Cannot exceed 50 shares"),
                                           MinValueValidator(1, message="Share number is less than 1")
                                       ])
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)
    contact_email = models.EmailField()

    def __str__(self):
        share_prefix = '[' + str(self.share_number) + ']: '
        name = self.first_name + ' ' + self.last_name
        return share_prefix + name


@register_snippet
class FamilyMember(models.Model):
    primary_shareholder = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="family")
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)
    contact_email = models.EmailField()

    def __str__(self):
        name = self.first_name + ' ' + self.last_name
        share_holder = '(' + str(self.primary_shareholder) + ') '
        return share_holder + name

    def clean(self):
        if not hasattr(self, 'primary_shareholder'):
            return
        # TODO move to settings
        maximum_family_members = 5
        if self.primary_shareholder.family.count() >= maximum_family_members:
            raise ValidationError("Cannot add more than %s family members" % str(maximum_family_members))


@register_snippet
class RoomType(models.Model):
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

    def __str__(self):  # bad plurals
        double_text = "" if self.double_beds == 0 else str(self.double_beds) + " double bed"
        bunk_text = "" if self.bunk_beds == 0 else str(self.bunk_beds) + " bunk beds"
        if bunk_text == "" or double_text == "":
            join_text = ""
        else:
            join_text = ", "
        return double_text + join_text + bunk_text


@register_snippet
class Room(models.Model):
    # TODO validators to settings
    config = models.ForeignKey(Config, on_delete=models.PROTECT, related_name="rooms")
    room_number = models.IntegerField(primary_key=True, validators=[
        MaxValueValidator(9, "Exceeds maximum rooms"),
        MinValueValidator(1),
    ])
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT)

    def __str__(self):
        return str(self.room_number) + ': ' + str(self.room_type)


@register_snippet
class Season(models.Model):
    config = models.ForeignKey(Config, on_delete=models.PROTECT, related_name="seasons")

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
    start_month = models.IntegerField(choices=Months,
                                      help_text="The season will begin at the first day of the selected month")
    end_month = models.IntegerField(choices=Months,
                                    help_text="The season will end at the end of the last day of the selected month")
    season_is_peak = models.BooleanField()

    panels = [
        FieldPanel("config"),
        FieldPanel("season_name"),
        FieldPanel("max_monthly_room_weeks"),
        FieldRowPanel([
            FieldPanel("start_month"),
            FieldPanel("end_month"),
            ]),
        FieldPanel("season_is_peak"),
    ]

    def __str__(self):
        return self.season_name

    def clean(self):
        # make sure correct stuff is set
        if not hasattr(self, 'config') or self.start_month is None or self.end_month is None:
            return
        # compare like-kinded seasons
        if self.season_is_peak:
            other_seasons = self.config.seasons.filter(season_is_peak=True)
        else:
            other_seasons = self.config.seasons.filter(season_is_peak=False)
        this_start = self.start_month
        this_end = self.end_month
        for s in other_seasons:
            # do seasons overlap
            if s.start_month <= this_end or s.end_month >= this_start:
                raise ValidationError("This season shares months with %s" % s.__str__())

@register_snippet
class BookingType(models.Model):
    config = models.ForeignKey(Config, on_delete=models.PROTECT, related_name="booking_types")
    booking_type_name = models.CharField(max_length=128)
    rate = models.DecimalField(max_digits=8, decimal_places=2)
    is_full_week_only = models.BooleanField()
    banned_rooms = models.ManyToManyField(Room, blank=True)
    season_active = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="booking_types")
    minimum_rooms = models.IntegerField("Minimum number of booked rooms")

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
            FieldPanel("is_full_week_only")
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
        similar_priority_bookings = self.season_active.booking_types.filter(priority_rank=self.priority_rank)
        if similar_priority_bookings.count() > 0:
            raise ValidationError("Overlapping priority with BookingType: %s" % similar_priority_bookings.get().booking_type_name)