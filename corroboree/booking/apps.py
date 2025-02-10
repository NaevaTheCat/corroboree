from django.apps import AppConfig

class BookingAppConfig(AppConfig):
    name = 'corroboree.booking'

    def ready(self):
        import corroboree.booking.signals