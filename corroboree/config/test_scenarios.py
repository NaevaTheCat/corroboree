from dataclasses import dataclass, field
from corroboree.config.factories import (
    ConfigFactory, MemberFactory, FamilyMemberFactory,
    RoomTypeFactory, RoomFactory, SeasonFactory, BookingTypeFactory,
)
from corroboree.config.models import Season, BookingType

"""
Reusable 'standard' Config scenario for booking-engine tests.

Mirrors a realistic production config: 2 members with family, 9 rooms
across 2 room types, 3 seasons, and 7 booking types.
"""

@dataclass
class StandardConfig:
    config: object
    members: dict = field(default_factory=dict)
    room_types: dict = field(default_factory=dict)
    rooms: dict = field(default_factory=dict)
    seasons: dict = field(default_factory=dict)
    booking_types: dict = field(default_factory=dict)


def build_standard_config() -> StandardConfig:
    config = ConfigFactory()

    # --- Members: 2 members, each with themselves and one other as family members ---
    members = {}
    for i, name in enumerate(["Alice", "Bob"], start=1):
        member = MemberFactory(config=config, share_number=i, first_name=name, last_name="Owner")
        FamilyMemberFactory(primary_shareholder=member, first_name=name, last_name="Owner")  # the shareholder themselves
        FamilyMemberFactory(primary_shareholder=member, first_name=f"{name}Spouse", last_name="Owner")
        members[name] = member

    # --- Room types ---
    four_bunk = RoomTypeFactory(config=config, double_beds=0, bunk_beds=4)
    double_two_bunk = RoomTypeFactory(config=config, double_beds=1, bunk_beds=2)
    room_types = {"four_bunk": four_bunk, "double_two_bunk": double_two_bunk}

    # --- Rooms ---
    rooms = {}
    four_bunk_numbers = {1, 8, 9}
    for number in range(1, 10):
        room_type = four_bunk if number in four_bunk_numbers else double_two_bunk
        rooms[str(number)] = RoomFactory(config=config, room_number=number, room_type=room_type)

    # --- Seasons summer: Oct-June, winter: June-Sept, winter_peak: August ---
    summer = SeasonFactory(
        config=config, season_name="Summer",
        start_month=Season.Months.October, end_month=Season.Months.June,
        season_is_peak=False, requires_strict_weeks=False,
    )
    winter = SeasonFactory(
        config=config, season_name="Winter",
        start_month=Season.Months.June, end_month=Season.Months.September,
        season_is_peak=False, requires_strict_weeks=True,
    )
    winter_peak = SeasonFactory(
        config=config, season_name="Winter Peak",
        start_month=Season.Months.August, end_month=Season.Months.August,
        season_is_peak=True, requires_strict_weeks=True,
    )
    seasons = {"summer": summer, "winter": winter, "winter_peak": winter_peak}

    # Double Bed rooms need to be banned for daily winter bookings
    double_bed_rooms = [r for r in rooms.values() if r.room_type == double_two_bunk]

    # --- Booking types ---
    # Based on production ~2026
    booking_types = {
        "summer_daily": BookingTypeFactory(
            config=config, season_active=summer, booking_type_name="Summer Daily",
            rate="105.00", is_full_week_only=False, priority_rank=BookingType.Priorities.LOW
        ),
        "summer_weekly": BookingTypeFactory(
            config=config, season_active=summer, booking_type_name="Summer Weekly",
            rate="250.00", is_full_week_only=True, sets_weekly_rate_cap=True,
            priority_rank=BookingType.Priorities.MEDIUM,
        ),
        "summer_whole_lodge": BookingTypeFactory(
            config=config, season_active=summer, booking_type_name="Summer Whole Lodge",
            rate="1500.00", is_full_week_only=True, is_flat_rate=True,
            minimum_rooms=9, priority_rank=BookingType.Priorities.HIGH,
        ),
        "winter_daily": BookingTypeFactory(
            config=config, season_active=winter, booking_type_name="Winter Daily",
            rate="135.00", is_full_week_only=False, requires_flexible_booking_period=True,
            priority_rank=BookingType.Priorities.LOW, banned_rooms=double_bed_rooms,
        ),
        "winter_weekly": BookingTypeFactory(
            config=config, season_active=winter, booking_type_name="Winter Weekly",
            rate="380.00", is_full_week_only=True, sets_weekly_rate_cap=True,
            priority_rank=BookingType.Priorities.MEDIUM,
        ),
        "winter_peak_daily": BookingTypeFactory(
            config=config, season_active=winter_peak, booking_type_name="Winter Peak Daily",
            rate="135.00", is_full_week_only=False, requires_flexible_booking_period=True,
            banned_rooms=double_bed_rooms, priority_rank=BookingType.Priorities.LOW,
        ),
        "winter_peak_weekly": BookingTypeFactory(
            config=config, season_active=winter_peak, booking_type_name="Winter Peak Weekly",
            rate="380.00", is_full_week_only=True, sets_weekly_rate_cap=True,
            priority_rank=BookingType.Priorities.MEDIUM,
        ),
    }

    return StandardConfig(
        config=config, members=members, room_types=room_types,
        rooms=rooms, seasons=seasons, booking_types=booking_types,
    )