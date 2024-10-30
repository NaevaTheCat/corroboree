from django import template

from django.conf import settings

register = template.Library()


@register.simple_tag
def paypal_client_id():
    return settings.PAYPAL_CLIENT_ID
