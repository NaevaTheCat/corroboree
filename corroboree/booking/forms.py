from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator

from wagtail.admin import widgets

import datetime

from corroboree.config import models as config
from corroboree.booking.models import BookingRecord
from corroboree.booking.logic import check_season_rules


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
        today = datetime.date.today()
        max_weeks_till_booking = config.Config.objects.get().max_weeks_till_booking
        max_weeks_ahead_start = datetime.timedelta(
            weeks=max_weeks_till_booking
        )
        max_weeks_ahead_end = datetime.timedelta(
            weeks=(1 + max_weeks_till_booking)
        )
        if start_date and end_date:
            if start_date > today + max_weeks_ahead_start:
                raise forms.ValidationError(
                    "Start date is more than %s weeks ahead" % max_weeks_till_booking
                )
            if not end_date > start_date:
                raise forms.ValidationError(
                    "End date must be after start date"
                )
            if end_date > today + max_weeks_ahead_end:
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
