import datetime
import pytz

from django import forms
from django.core.validators import MinValueValidator
from wagtail.admin import widgets

from corroboree.booking.models import get_booking_types, check_season_rules, booked_rooms, last_weekday_date, create_booking_cart_periods
from corroboree.config import models as config


# TODO round to week chunks
class BookingDateRangeForm(forms.Form):
    arrival_date = forms.DateField(
        label="Arrival date",
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
    departure_date = forms.DateField(
        label="Departure date",
        widget=widgets.AdminDateInput(
            attrs={
                "placeholder": "dd-mm-yyyy",
                "type": "date",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        conf = config.Config.objects.get()
        arrival_date = cleaned_data.get("arrival_date")
        departure_date = cleaned_data.get("departure_date")
        # Time of day rollover checking
        tod_rollover = conf.time_of_day_rollover
        aest_now = datetime.datetime.now(pytz.timezone('Australia/Sydney'))
        compare_date = aest_now.date() if aest_now.time() >= tod_rollover else aest_now.date() - datetime.timedelta(days=1)
        last_week_start = last_weekday_date(compare_date, conf.week_start_day)
        max_weeks_till_booking = conf.max_weeks_till_booking
        max_weeks_ahead_start = datetime.timedelta(
            weeks=max_weeks_till_booking
        )
        max_weeks_ahead_end = datetime.timedelta(
            weeks=(1 + max_weeks_till_booking)
        )
        if arrival_date and departure_date:
            if arrival_date > last_week_start + max_weeks_ahead_start:
                raise forms.ValidationError(
                    "Arrival date is more than %s weeks ahead" % max_weeks_till_booking
                )
            if not departure_date > arrival_date:
                raise forms.ValidationError(
                    "Departure date must be after arrival date"
                )
            if departure_date > last_week_start + max_weeks_ahead_end:
                raise forms.ValidationError(
                    "Departure date is more than %s weeks ahead" % (max_weeks_till_booking + 1)
                )


class BookingRoomChoosingForm(forms.Form):
    arrival_date = forms.DateField(
        label="Arrival date",
        widget=widgets.AdminDateInput(
            attrs={
                "placeholder": "dd-mm-yyyy",
                "type": "date",
                "readonly": "readonly",
            }
        ),
    )
    departure_date = forms.DateField(
        label="Departure date",
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

    def __init__(self, *args, arrival_date=None, departure_date=None, member=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.member = member
        if arrival_date is not None and departure_date is not None:
            booked_room_ids = booked_rooms(arrival_date, departure_date)
            booking_periods = create_booking_cart_periods(arrival_date, departure_date)
            banned_rooms = config.Room.objects.none()  # empty queryset we will build up to filter available rooms with
            for p in booking_periods:
                banned_rooms = banned_rooms.union(p.banned_rooms())
            banned_room_ids = banned_rooms.values_list('room_number')
            available_rooms = config.Room.objects.exclude(pk__in=booked_room_ids).exclude(pk__in=banned_room_ids)
            self.fields["room_selection"].queryset = available_rooms
            self.fields["arrival_date"].initial = arrival_date
            self.fields["departure_date"].initial = departure_date

    def clean(self):
        cleaned_data = super().clean()
        room_selection = cleaned_data.get('room_selection')
        if room_selection is None:
            raise forms.ValidationError(
                'You must select at least one room'
            )
        check_season_rules(
            member=self.member,
            arrival_date=cleaned_data.get('arrival_date'),
            departure_date=cleaned_data.get('departure_date'),
            rooms=room_selection,
        )


# Custom field for member_in_attendance names
class MiAModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.full_name()


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


