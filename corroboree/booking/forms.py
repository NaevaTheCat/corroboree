from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

from wagtail.admin import widgets

import datetime

from corroboree.config.models import seasons_in_date_range
from corroboree.config import models as config
from corroboree.booking.models import BookingRecord, bookings_for_member_in_range


# TODO round to week chunks
class BookingDateRangeForm(forms.Form):
    start_date = forms.DateField(
        label="Start date",
        validators=[
            MinValueValidator(datetime.date.today()),
        ],
        widget=widgets.AdminDateInput(
            attrs={
                "placeholder": "dd-mm-yyyy",
                "type": "date",
            }
        ),
    )
    end_date = forms.DateField(
        label="End date",
        widget=widgets.AdminDateInput(
            attrs={
                "placeholder": "dd-mm-yyyy",
                "type": "date",
            }
        ),
    )

    # TODO release weeks 1 chunk at a time. Rounding needed
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        last_sunday = last_weekday_date(datetime.date.today(), 6)
        max_weeks_till_booking = config.Config.objects.get().max_weeks_till_booking
        max_weeks_ahead_start = datetime.timedelta(
            weeks=max_weeks_till_booking
        )
        max_weeks_ahead_end = datetime.timedelta(
            weeks=(1 + max_weeks_till_booking)
        )
        if start_date and end_date:
            if start_date > last_sunday + max_weeks_ahead_start:
                raise forms.ValidationError(
                    "Start date is more than %s weeks ahead" % max_weeks_till_booking
                )
            if not end_date > start_date:
                raise forms.ValidationError(
                    "End date must be after start date"
                )
            if end_date > last_sunday + max_weeks_ahead_end:
                raise forms.ValidationError(
                    "End date is more than %s weeks ahead" % (max_weeks_till_booking + 1)
                )


class BookingRoomChoosingForm(forms.Form):
    start_date = forms.DateField(
        label="Start date",
        widget=widgets.AdminDateInput(
            attrs={
                "placeholder": "dd-mm-yyyy",
                "type": "date",
                "readonly": "readonly",
            }
        ),
    )
    end_date = forms.DateField(
        label="End date",
        widget=widgets.AdminDateInput(
            attrs={
                "placeholder": "dd-mm-yyyy",
                "type": "date",
                "readonly": "readonly",
            }
        ),
    )
    room_selection = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
    )
    member = forms.ModelChoiceField(
        queryset=config.Member.objects.all(),
        widget=forms.Select(
            attrs={
                "readonly": "readonly",
            }
        ),
    )

    def __init__(self, *args, start_date=None, end_date=None, member=None, **kwargs):
        super().__init__(*args, **kwargs)
        if start_date is not None and end_date is not None:
            current_booking_records = BookingRecord.objects.filter(
                end_date__gt=datetime.date.today(),
                start_date__lt=end_date,
            ).exclude(status__exact=BookingRecord.BookingRecordStatus.CANCELLED)
            overlapping_bookings = current_booking_records.exclude(
                start_date__gte=end_date).exclude(
                end_date__lte=start_date,
            )
            booked_room_ids = overlapping_bookings.values_list('rooms__room_number', flat=True)
            available_rooms = config.Room.objects.exclude(pk__in=list(booked_room_ids)) # breaks on None, which should be impossible, if fed the raw queryset.
            self.fields["room_selection"].queryset = available_rooms
            self.fields["start_date"].initial = start_date
            self.fields["end_date"].initial = end_date
            self.fields["member"].initial = member

    def clean(self):
        cleaned_data = super().clean()
        room_selection = cleaned_data.get('room_selection')
        if room_selection is None:
            raise forms.ValidationError(
                'You must select at least one room'
            )
        check_season_rules(
            member=cleaned_data.get('member'),
            start_date=cleaned_data.get('start_date'),
            end_date=cleaned_data.get('end_date'),
            rooms=room_selection,
        )


def check_season_rules(member: config.Member, start_date: datetime.date, end_date: datetime.date, rooms: [config.Room]):
    conf = config.Config.objects.get()  # only valid for single config
    for start, end in date_range_to_month_ranges(start_date, end_date):
        overlapping_bookings = bookings_for_member_in_range(member, start, end)
        occupancy_array = room_occupancy_array(start, end, rooms, overlapping_bookings)
        season_in_month = seasons_in_date_range(conf, start, end)
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
                            date=start + datetime.timedelta(sum_rooms.index(max(sum_rooms))),
                        )
                    )
            if season_in_month.max_monthly_room_weeks is not None:
                if sum(sum_rooms)/7 > season_in_month.max_monthly_room_weeks:
                    raise ValidationError(
                        'This booking exceeds the {max} room-weeks limit for {season} during {month}'.format(
                            max=season_in_month.max_monthly_room_weeks,
                            season=season_in_month.season_name,
                            month=start.strftime('%B')
                        )
                    )


def last_weekday_date(date: datetime.date, weekday=6):
    """Given a date and weekday, return the date of the last weekday (datetime ints [0-6])"""
    date_day = date.weekday()
    delta = datetime.timedelta((7 - (weekday - date_day)) % 7)
    return date - delta


def date_range_to_month_ranges(start: datetime.date, end: datetime.date):
    """Splits a start and end date into ranges by month

    Used for checking season rules"""
    result = []
    while True:
        if start.month == 12:
            next_month = start.replace(year=start.year+1, month=1, day=1)
        else:
            next_month = start.replace(month=start.month+1, day=1)
        if next_month > end:
            break
        result.append((start, last_day_of_month(start)))
        start = next_month
    result.append((start, end))
    return result


def last_day_of_month(day: datetime.date):
    next_month = day.replace(day=28) + datetime.timedelta(days=4)
    return next_month - datetime.timedelta(days=next_month.day)


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
