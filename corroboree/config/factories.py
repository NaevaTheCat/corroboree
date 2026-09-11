import factory
from corroboree.config.models import Config, Member, FamilyMember, RoomType, Room, Season, BookingType


class ConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Config

    max_weeks_till_booking = 26
    time_of_day_rollover = "10:00"
    week_start_day = Config.Weekday.Monday
    flexible_booking_weeks = 13
    last_minute_booking_weeks = 2
    number_of_rooms = 9
    maximum_family_members = 10


class MemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Member

    config = factory.SubFactory(ConfigFactory)
    share_number = factory.Sequence(lambda n: n + 1)
    first_name = factory.Sequence(lambda n: f"Member{n}")
    last_name = "Test"
    contact_email = factory.LazyAttribute(lambda o: f"{o.first_name.lower()}@example.com")
    contact_phone = "0400000000"


class FamilyMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FamilyMember

    primary_shareholder = factory.SubFactory(MemberFactory)
    first_name = factory.Sequence(lambda n: f"Family{n}")
    last_name = "Test"
    contact_email = factory.LazyAttribute(lambda o: f"{o.first_name.lower()}@example.com")
    contact_phone = "0400000001"


class RoomTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RoomType

    config = factory.SubFactory(ConfigFactory)
    double_beds = 0
    bunk_beds = 4


class RoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Room

    config = factory.SubFactory(ConfigFactory)
    room_number = factory.Sequence(lambda n: n + 1)
    room_type = factory.SubFactory(RoomTypeFactory)


class SeasonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Season

    config = factory.SubFactory(ConfigFactory)
    season_name = factory.Sequence(lambda n: f"Season{n}")
    max_monthly_room_weeks = None
    start_month = Season.Months.January
    end_month = Season.Months.December
    season_is_peak = False
    requires_strict_weeks = False


class BookingTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BookingType

    config = factory.SubFactory(ConfigFactory)
    booking_type_name = factory.Sequence(lambda n: f"BookingType{n}")
    rate = "100.00"
    is_full_week_only = False
    sets_weekly_rate_cap = False
    requires_flexible_booking_period = False
    requires_last_minute_booking_period = False
    is_flat_rate = False
    season_active = factory.SubFactory(SeasonFactory)
    minimum_rooms = 0
    priority_rank = BookingType.Priorities.LOW

    @factory.post_generation
    def banned_rooms(self, create, extracted, **kwargs):
        # lets you write BookingTypeFactory(banned_rooms=[room1, room2])
        if not create or not extracted:
            return
        self.banned_rooms.set(extracted)