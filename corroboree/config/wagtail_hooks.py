from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from corroboree.config.models import Config, Member, RoomType, Room, Season, BookingType, FamilyMember


class FamilyMemberViewSet(SnippetViewSet):
    model = FamilyMember
    icon = 'user'
    list_display = ['name', 'contact_email', 'primary_shareholder']
    copy_view_enabled = False
    list_filter = {
        'primary_shareholder__last_name': ['icontains'],
        'primary_shareholder__share_number': ['exact'],
        'last_name': ['icontains']
    }


class BookingTypeViewSet(SnippetViewSet):
    model = BookingType
    icon = 'form'
    list_display = ['booking_type_name', 'season_active', 'rate', 'is_full_week_only']
    copy_view_enabled = False
    list_filter = {
        'season_active': ['exact'],
        'booking_type_name': ['icontains'],
    }


register_snippet(Config)
register_snippet(Member)
register_snippet(FamilyMemberViewSet)
register_snippet(RoomType)
register_snippet(Room)
register_snippet(Season)
register_snippet(BookingTypeViewSet)
