from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from corroboree.config.models import Config, Member, RoomType, Room, Season, BookingType, FamilyMember

class MemberViewSet(SnippetViewSet):
    model = Member
    icon = 'user'
    list_display = ['last_name', 'first_name', 'share_number', 'contact_email', 'get_member_account']
    ordering = ['share_number']
    copy_view_enabled = False
    list_filter = {
        'last_name' : ['icontains'],
        'first_name' : ['icontains'],
        'share_number' : ['exact']
    }


class FamilyMemberViewSet(SnippetViewSet):
    model = FamilyMember
    icon = 'user'
    list_display = ['last_name', 'first_name', 'contact_email', 'primary_shareholder']
    ordering = ['primary_shareholder']
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
register_snippet(MemberViewSet)
register_snippet(FamilyMemberViewSet)
register_snippet(RoomType)
register_snippet(Room)
register_snippet(Season)
register_snippet(BookingTypeViewSet)
