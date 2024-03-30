from django.db import models


class Config(models.Model):
    max_weeks_till_booking = models.IntegerField(default=26)
    time_of_day_rollover = models.TimeField(
        help_text="What time of day to open bookings for the day max_weeks_till_booking from now")


class Member(models.Model):
    config = models.ForeignKey(Config, on_delete=models.PROTECT)
    share_number = models.IntegerField(primary_key=True)
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)
    contact_email = models.EmailField()


class FamilyMember(models.Model):
    primary_shareholder = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="family")
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)


class Room(models.Model):
    config = models.ForeignKey(Config, on_delete=models.PROTECT, related_name="rooms")
    room_number = models.IntegerField(primary_key=True)
    room_description = models.CharField(max_length=128)
    max_occupants = models.IntegerField("Maximum Room Occupants", default=4)


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
    max_monthly_room_weeks = models.IntegerField()
    start_month = models.IntegerField(choices=Months,
                                      help_text="The season will begin at the first day of the selected month")
    end_month = models.IntegerField(choices=Months,
                                    help_text="The season will end at the end of the last day of the prior month")
    season_is_peak = models.BooleanField()


class BookingType(models.Model):
    config = models.ForeignKey(Config, on_delete=models.PROTECT, related_name="booking_types")
    booking_type_name = models.CharField(max_length=128)
    rate = models.IntegerField()
    is_full_week_only = models.BooleanField()
    banned_rooms = models.ManyToManyField(Room)
    seasons_active = models.ManyToManyField(Season, related_name="booking_types")
    minimum_rooms = models.IntegerField("Minimum number of booked rooms")

    class Priorities(models.IntegerChoices):
        HIGH = 1
        MEDIUM = 2
        LOW = 3

    priority_rank = models.IntegerField(choices=Priorities, default=Priorities.LOW,
                                        help_text="Priority booking takes when calculating costs when multiple kinds are valid.")
