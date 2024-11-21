import datetime
import pytz

from django import forms
from django.core.validators import MinValueValidator
from wagtail.admin import widgets

from corroboree.booking.models import BookingRecord, get_booking_types, check_season_rules
from corroboree.config import models as config


# TODO round to week chunks
class BookingDateRangeForm(forms.Form):
    start_date = forms.DateField(
        label="Start date",
        validators=[
            MinValueValidator(datetime.datetime.now(pytz.timezone('Australia/Sydney')).date()),
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
        conf = config.Config.objects.get()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        # Time of day rollover checking
        tod_rollover = config.Config.objects.get().time_of_day_rollover
        aest_now = datetime.datetime.now(pytz.timezone('Australia/Sydney'))
        compare_date = aest_now.date() if aest_now.time() >= tod_rollover else aest_now.date() - datetime.timedelta(days=1)
        last_sunday = last_weekday_date(compare_date, conf.week_start_day)
        max_weeks_till_booking = conf.max_weeks_till_booking
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

    def __init__(self, *args, start_date=None, end_date=None, member=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.member = member
        if start_date is not None and end_date is not None:
            current_booking_records = BookingRecord.live_objects.filter(
                end_date__gt=datetime.date.today(),
                start_date__lt=end_date,
            )
            overlapping_bookings = current_booking_records.exclude(
                start_date__gte=end_date).exclude(
                end_date__lte=start_date,
            )
            booked_room_ids = overlapping_bookings.values_list('rooms__room_number', flat=True)
            possible_booking_types = get_booking_types(conf=config.Config.objects.get(),
                                                       start_date=start_date,
                                                       end_date=end_date)
            banned_rooms = config.Room.objects.none()  # empty queryset we will build up to filter available rooms with
            for day in possible_booking_types:
                daily_banned_rooms = config.Room.objects.all()
                if possible_booking_types[day].count() == 0:
                    # No bookings possible on a day/week during range i.e. all rooms are banned and we can stop looking
                    daily_banned_rooms = config.Room.objects.all()
                else:
                    for booking_type in possible_booking_types[day]:
                        this_banned_rooms = booking_type.banned_rooms.all()
                        # Set intersection all rooms and banned rooms. Only leaves rooms that aren't available in any way
                        daily_banned_rooms = daily_banned_rooms & this_banned_rooms
                banned_rooms = banned_rooms | daily_banned_rooms
            available_rooms = config.Room.objects.exclude(pk__in=list(booked_room_ids)).exclude(pk__in=banned_rooms)
            self.fields["room_selection"].queryset = available_rooms
            self.fields["start_date"].initial = start_date
            self.fields["end_date"].initial = end_date

    def clean(self):
        cleaned_data = super().clean()
        room_selection = cleaned_data.get('room_selection')
        if room_selection is None:
            raise forms.ValidationError(
                'You must select at least one room'
            )
        check_season_rules(
            member=self.member,
            start_date=cleaned_data.get('start_date'),
            end_date=cleaned_data.get('end_date'),
            rooms=room_selection,
        )


# Custom field for member_in_attendance names
class MiAModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.first_name + ' ' + obj.last_name


class BookingRecordMemberInAttendanceForm(forms.Form):
    member_in_attendance = MiAModelChoiceField(queryset=config.FamilyMember.objects.all())

    def __init__(self, *args, member=None, member_in_attendance=None, **kwargs):
        super().__init__(*args, **kwargs)
        if member is not None:
            queryset = config.Member.objects.get(pk=member.share_number).family.all()
            self.fields['member_in_attendance'].queryset = queryset
        if member_in_attendance is not None:
            self.fields['member_in_attendance'].initial = member_in_attendance


class GuestForm(forms.Form):
    first_name = forms.CharField(max_length=64, required=False)
    last_name = forms.CharField(max_length=64, required=False)
    email = forms.EmailField(label='Contact Email', required=False)


def last_weekday_date(date: datetime.date, weekday=5):
    """Given a date and weekday, return the date of the last weekday (datetime ints [0-6])"""
    date_day = date.weekday()
    delta = datetime.timedelta((7 - (weekday - date_day)) % 7)
    return date - delta
