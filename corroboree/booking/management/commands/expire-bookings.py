from django.core.management.base import BaseCommand, CommandError
from corroboree.booking.models import BookingRecord
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = "Sets expired in progress or submitted bookings to cancelled"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which bookings would be cancelled without saving changes'
        )

    def handle(self, *args, **options):
        status = BookingRecord.BookingRecordStatus
        now = timezone.now()
        # TODO: settings?
        in_progress_limit = now - timedelta(minutes=30)
        submitted_limit = now - timedelta(hours=24)
        in_progress_expired = BookingRecord.objects.filter(
            status=status.IN_PROGRESS,
            last_updated__lt = in_progress_limit
        )
        submitted_expired = BookingRecord.objects.filter(
            status=status.SUBMITTED,
            last_updated__lt=submitted_limit
        )
        if options['dry_run']:
            self.stdout.write('IN_PROGRESS bookings to cancel:')
            for booking in in_progress_expired:
                self.stdout.write(f'{booking}')
            self.stdout.write('SUBMITTED bookings to cancel:')
            for booking in submitted_expired:
                self.stdout.write(f'{booking}')
        else:
            # Update would be more efficient, but lose safeguards that might be implemented
            for booking in in_progress_expired:
                booking.update_status(status.CANCELLED)
            for booking in submitted_expired:
                booking.update_status(status.CANCELLED)
            self.stdout.write(self.style.SUCCESS(
                'Cancelled {in_progress_count} bookings in progress and {submitted_count} submitted bookings.'.format(
                    in_progress_count=in_progress_expired.count(),
                    submitted_count=submitted_expired.count()
                )
            ))