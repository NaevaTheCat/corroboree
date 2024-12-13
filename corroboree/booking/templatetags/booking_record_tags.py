from django import template

from typing import Literal

from wagtail.models import Site

from corroboree.booking.models import BookingRecord

register = template.Library()


RenderMode = Literal[
    'IN_PROGRESS',
    'SUMMARY',
    'COST_SUMMARY',
    'FULL',
]  # see template for what it does


@register.inclusion_tag('templatetags/booking_record.html')
def render_booking_record(booking: BookingRecord, render_mode: RenderMode):
    arrival_date = booking.arrival_date
    departure_date = booking.departure_date
    rooms = booking.rooms.all()
    member_in_attendance = booking.member_in_attendance
    cost = booking.cost
    status = booking.status
    payment_status = booking.payment_status
    attendees = booking.other_attendees
    attendees_cleaned = {}
    for key in attendees.keys():
        empty = True
        guest = attendees[key]
        for key2 in guest.keys():
            empty = empty and True if guest[key2] == '' else False
        if not empty:
            attendees_cleaned[key] = guest
    return {
        'arrival_date': arrival_date,
        'departure_date': departure_date,
        'rooms': rooms,
        'member_in_attendance': member_in_attendance,
        'cost': cost,
        'status': status,
        'payment_status': payment_status,
        'attendees': attendees_cleaned,
        'render_mode': render_mode,
    }

