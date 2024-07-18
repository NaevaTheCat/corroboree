import corroboree.config.models as config
import corroboree.booking.models as booking

from django.db.models import F, Q
from django.forms import ValidationError

import datetime


# TODO: Sunday to Sunday release logic

def calculate_booking_cart():
    pass


def check_season_rules(member: config.Member, start_date: datetime.date, end_date: datetime.date, rooms: [config.Room]):
    conf = config.Config.objects.get() # only valid for single config
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
        for day in range(0,len(occupancy_array[0])):
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


def bookings_for_member_in_range(member: config.Member, start_date: datetime.date, end_date: datetime.date):
    """Given a member and a date range returns bookings for that member within that date range (including partially)"""
    bookings = member.bookings.exclude(end_date__lte=start_date).exclude(start_date__gte=end_date)
    return bookings


def room_occupancy_array(start_date: datetime.date, end_date: datetime.date, rooms: [config.Room],
                         other_bookings: [booking.BookingRecord]):
    """create a list of lists where the inner lists represent the number of rooms booked by that booking on that day"""
    # on reflection this might be overkill and could probably just be a list of the sum of rooms booked on that day?
    array = []
    length = (end_date - start_date).days
    array.append([len(rooms)] * length)
    for this_booking in other_bookings:
        num_rooms = this_booking.rooms.all().count()
        # pad a list with the days vacant at start or end so we know the rooms on each day
        start_delta = max(0, (this_booking.start_date - start_date).days)
        end_delta = max(0, (end_date - this_booking.end_date).days)
        array.append([0] * start_delta + [num_rooms] * (length - (start_delta + end_delta)) + [0] * end_delta)
    return array


def dates_to_weeks(start_date: datetime.date, end_date: datetime.date, week_start_day=6):
    """For a date range and day of week return the number of weeks and surrounding 'spare' days

    Using datetime weekday ints monday=0 sunday=6.
    """
    start_weekday = start_date.weekday()
    end_weekday = end_date.weekday()
    leading_days = (week_start_day - start_weekday) % 7
    trailing_days = (7 - (week_start_day - end_weekday)) % 7
    from_week = start_date + datetime.timedelta(days=leading_days)
    till_week = end_date - datetime.timedelta(days=trailing_days)
    weeks = int((till_week - from_week).days / 7)
    return leading_days, weeks, trailing_days


def seasons_in_date_range(conf: config.Config, start_date: datetime.date, end_date: datetime.date):
    """Returns a Queryset of seasons that are active during any part of a date range"""
    start_month = start_date.month
    end_month = end_date.month
    # given months can wrap need to capture the 4 cases of comparison
    if start_month <= end_month:
        seasons = conf.seasons.exclude(
            Q(start_month__lte=F('end_month')) & (Q(start_month__gt=end_month) | Q(end_month__lt=start_month))
        ).exclude(
            Q(start_month__gt=F('end_month')) & (Q(end_month__lt=start_month) & Q(start_month__gt=end_month))
        )
    else:
        seasons = conf.seasons.exclude(
            Q(start_month__lte=F('end_month')) & (Q(start_month__gt=end_month) & Q(end_month__lt=start_month))
        )
    return seasons


def get_booking_types_by_priority(start):
    pass
