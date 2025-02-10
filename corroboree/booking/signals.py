from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import BookingRecord

@receiver(post_save, sender=BookingRecord)
def send_admin_email(sender, instance: BookingRecord, **kwargs):
    """Send an email if an admin tweaked or created the record and thought it should happen"""
    if instance.send_admin_email:
        instance.send_related_email(subject='Neige Booking: {start} - {end}'.format(
                                start=instance.arrival_date,
                                end=instance.departure_date
                            ),
                            email_text='An Administrator created or updated the following booking. '
                                       'Please contact the booking administrator with any concerns.')
        BookingRecord.objects.filter(pk=instance.pk).update(send_admin_email=False)