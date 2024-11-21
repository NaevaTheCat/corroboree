from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from corroboree.booking.models import BookingRecord
from django.db import transaction
from django.conf import settings


class Command(BaseCommand):
    help = 'Send reminder emails for bookings starting within the next week'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        week_ahead = now + timedelta(weeks=1)

        bookings = BookingRecord.live_objects.filter(
            start_date__lte=week_ahead, start_date__gt=now, reminder_sent=False
        )

        for booking in bookings:
            try:
                with transaction.atomic():
                    booking.send_related_email(
                        subject=f'Neige Booking Reminder: {booking.start_date} - {booking.end_date}',
                        email_text='Please confirm the guests for your upcoming booking:'
                    )
                    booking.reminder_sent = True
                    booking.save()
                    self.stdout.write(self.style.SUCCESS(f'Successfully sent reminder for booking {booking.id}'))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'Failed to send reminder for booking {booking.id}: {exc}'))