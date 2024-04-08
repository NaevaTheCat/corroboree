from django.db import models
from django.db.models import F

from wagtail.admin.panels import FieldPanel
from wagtail.snippets.models import register_snippet


@register_snippet
class Config(models.Model):
    max_weeks_till_booking = models.IntegerField(default=26)
    time_of_day_rollover = models.TimeField(
        help_text="What time of day to open bookings for the day max_weeks_till_booking from now")


@register_snippet
class Member(models.Model):
    config = models.ForeignKey(Config, on_delete=models.PROTECT)
    share_number = models.IntegerField(primary_key=True)
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

    def __str__(self):
        name = self.first_name + ' ' + self.last_name
        share_holder = '(' + str(self.primary_shareholder) + ') '
        return share_holder + name


@register_snippet
class RoomType(models.Model):
    double_beds = models.IntegerField()
    bunk_beds = models.IntegerField()
    max_occupants = models.GeneratedField(
        expression=F("double_beds") * 2 + F("bunk_beds"),
        output_field=models.IntegerField(),
        db_persist=True)

    # TODO validate limits (e.g. negatives)

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
    config = models.ForeignKey(Config, on_delete=models.PROTECT, related_name="rooms")
    room_number = models.IntegerField(primary_key=True)
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
    max_monthly_room_weeks = models.IntegerField(blank=True, null=True)
    start_month = models.IntegerField(choices=Months,
                                      help_text="The season will begin at the first day of the selected month")
    end_month = models.IntegerField(choices=Months,
                                    help_text="The season will end at the end of the last day of the prior month")
    season_is_peak = models.BooleanField()

    def __str__(self):
        return self.season_name


@register_snippet
class BookingType(models.Model):
    config = models.ForeignKey(Config, on_delete=models.PROTECT, related_name="booking_types")
    booking_type_name = models.CharField(max_length=128)
    rate = models.IntegerField()
    is_full_week_only = models.BooleanField()
    banned_rooms = models.ManyToManyField(Room, blank=True, null=True)
    season_active = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="booking_types")
    minimum_rooms = models.IntegerField("Minimum number of booked rooms")

    class Priorities(models.IntegerChoices):
        HIGH = 1
        MEDIUM = 2
        LOW = 3

    priority_rank = models.IntegerField(choices=Priorities, default=Priorities.LOW,
                                        help_text="Priority booking takes when calculating costs when multiple kinds are valid.")

    def __str__(self):
        return self.booking_type_name
