from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from django_filters import FilterSet, ModelMultipleChoiceFilter, CharFilter, DateFilter, ChoiceFilter
from wagtail.admin.widgets import AdminDateInput
from wagtail.admin.panels import FieldPanel, FieldRowPanel
from django.forms import CheckboxSelectMultiple

from .models import BookingRecord
from corroboree.config import models as config

class BookingRecordFilter(FilterSet):
    rooms = ModelMultipleChoiceFilter(
        queryset=config.Room.objects.all(),
        widget=CheckboxSelectMultiple,
        label='Rooms',
        method='filter_rooms',
    )
    member_last_name = CharFilter(field_name='member__last_name', lookup_expr='iexact', label='Member Last Name')
    member_first_name = CharFilter(field_name='member__first_name', lookup_expr='iexact', label='Member First Name')
    member_in_attendance_last_name = CharFilter(field_name='member_in_attendance__last_name', lookup_expr='iexact',
                                                label='Member in Attendance Last Name')
    member_in_attendance_first_name = CharFilter(field_name='member_in_attendance__first_name', lookup_expr='iexact',
                                                 label='Member in Attendance First Name')
    arrival_date_lt = DateFilter(field_name='arrival_date', lookup_expr='lt', label='Arrival Date Before',
                               widget=AdminDateInput)
    arrival_date_gt = DateFilter(field_name='arrival_date', lookup_expr='gt', label='Arrival Date After',
                               widget=AdminDateInput)
    departure_date_lt = DateFilter(field_name='departure_date', lookup_expr='lt', label='Departure Date Before', widget=AdminDateInput)
    departure_date_gt = DateFilter(field_name='departure_date', lookup_expr='gt', label='Departure Date After', widget=AdminDateInput)
    status = ChoiceFilter(field_name='status', lookup_expr='exact', label='Status',
                          choices=BookingRecord.BookingRecordStatus)
    payment_status = ChoiceFilter(field_name='payment_status', lookup_expr='iexact', label='Payment Status',
                                  choices=BookingRecord.BookingRecordPaymentStatus)
    paypal_transaction_id = CharFilter(field_name='paypal_transaction_id', lookup_expr='exact',
                                       label='PayPal Transaction ID')
    cost_lt = CharFilter(field_name='cost', lookup_expr='lt', label='Cost Less Than')
    cost_gt = CharFilter(field_name='cost', lookup_expr='gt', label='Cost Greater Than')

    class Meta:
        model = BookingRecord
        fields = [
            'member_last_name',
            'member_first_name',
            'member_in_attendance_last_name',
            'member_in_attendance_first_name',
            'arrival_date_lt',
            'arrival_date_gt',
            'departure_date_lt',
            'departure_date_gt',
            'rooms',
        ]

    def filter_rooms(self, queryset, name, value):
        for room in value:
            queryset = queryset.filter(rooms=room)
        return queryset

class BookingRecordViewSet(SnippetViewSet):
    model = BookingRecord
    icon = 'form'
    menu_label = 'Bookings'
    menu_name = 'bookings'
    menu_order = 300
    add_to_admin_menu = True
    list_display = [
        'member',
        'arrival_date',
        'departure_date',
        'member_in_attendance',
        'status',
        'payment_status',
        'cost',
        'paypal_transaction_id',
        'rooms_list',
    ]
    list_export = [
        'member',
        'member_name_at_creation',
        'last_updated',
        'arrival_date',
        'departure_date',
        'member_in_attendance',
        'member_in_attendance_name_at_creation',
        'other_attendees',
        'status',
        'payment_status',
        'cost',
        'paypal_transaction_id',
        'rooms_list',
    ]
    list_per_page = 50
    copy_view_enabled = False
    inspect_view_enabled = True
    admin_url_namespace = 'bookings_view'
    base_url_path = 'internal/bookings'
    filterset_class = BookingRecordFilter

    panels = [
        FieldRowPanel([
            FieldPanel('member'),
            FieldPanel('member_name_at_creation')
        ]),
        FieldRowPanel([
            FieldPanel('member_in_attendance'),
            FieldPanel('member_in_attendance_name_at_creation')
        ]),
        FieldRowPanel([
            FieldPanel('arrival_date'),
            FieldPanel('departure_date'),
        ]),
        FieldPanel('rooms', widget=CheckboxSelectMultiple),
        FieldPanel('other_attendees'),
        FieldPanel('cost'),
        FieldRowPanel([
            FieldPanel('status'),
            FieldPanel('payment_status'),
            FieldPanel('paypal_transaction_id'),
        ]),
    ]


register_snippet(BookingRecordViewSet)