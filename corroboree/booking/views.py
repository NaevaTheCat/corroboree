from corroboree.booking.models import BookingRecord

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from corroboree.booking.models import BookingRecord

import logging

from django.conf import settings
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.logging.configuration.api_logging_configuration import LoggingConfiguration, \
    RequestLoggingConfiguration, ResponseLoggingConfiguration
from paypalserversdk.models.amount_with_breakdown import AmountWithBreakdown
from paypalserversdk.models.checkout_payment_intent import CheckoutPaymentIntent
from paypalserversdk.models.order_request import OrderRequest
from paypalserversdk.models.payee import Payee
from paypalserversdk.models.payment_source import PaymentSource
from paypalserversdk.models.pay_pal_experience_user_action import PayPalExperienceUserAction
from paypalserversdk.models.pay_pal_wallet import PayPalWallet
from paypalserversdk.models.pay_pal_wallet_experience_context import PayPalWalletExperienceContext
from paypalserversdk.models.purchase_unit_request import PurchaseUnitRequest
from paypalserversdk.models.shipping_preference import ShippingPreference
from paypalserversdk.paypalserversdk_client import PaypalserversdkClient, Environment
from paypalserversdk.exceptions.error_exception import ErrorException
from paypalserversdk.exceptions.api_exception import APIException
from paypalserversdk.models.payee_payment_method_preference import PayeePaymentMethodPreference

PAYPAL_CLIENT_ID = settings.PAYPAL_CLIENT_ID
PAYPAL_CLIENT_SECRET = settings.PAYPAL_CLIENT_SECRET
PAYPAL_MERCHANT_EMAIL = settings.PAYPAL_MERCHANT_EMAIL
PAYPAL_MERCHANT_ID = settings.PAYPAL_MERCHANT_ID

# Set paypal environment based on django
if settings.DEBUG == True:
    paypal_environment = Environment.SANDBOX
else:
    paypal_environment = Environment.PRODUCTION

client = PaypalserversdkClient(
    client_credentials_auth_credentials=ClientCredentialsAuthCredentials(
        o_auth_client_id=PAYPAL_CLIENT_ID,
        o_auth_client_secret=PAYPAL_CLIENT_SECRET
    ),
    environment=paypal_environment,
    logging_configuration=LoggingConfiguration(
        log_level=logging.INFO,
        request_logging_config=RequestLoggingConfiguration(
            log_body=True
        ),
        response_logging_config=ResponseLoggingConfiguration(
            log_headers=True,
            log_body=True,
        )
    )
)


def create_booking_order(request, booking_id):
    try:
        booking = BookingRecord.objects.get(id=booking_id)
        cost = booking.cost
        # TODO: fix this to fetch url parts via page object lookup?
        return_url = request.build_absolute_uri('/') + 'my-bookings/pay/success/?booking=' + str(booking_id)
        cancel_url = request.build_absolute_uri('/') + 'my-bookings/cancel/' + str(booking_id) + '/'
        billing_reference = booking.id
    except BookingRecord.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)
    orders_controller = client.orders
    collect = {
        'body': OrderRequest(
            intent=CheckoutPaymentIntent.CAPTURE,
            purchase_units=[
                PurchaseUnitRequest(
                    amount=AmountWithBreakdown(
                        currency_code='AUD',
                        value=str(cost)
                    ),
                    custom_id=billing_reference,
                    description='Neigejindi booking: %s' % booking_id,
                    payee=Payee(
                        email_address=PAYPAL_MERCHANT_EMAIL,
                        merchant_id=PAYPAL_MERCHANT_ID
                    )
                )
            ],
            payment_source=PaymentSource(
                paypal=PayPalWallet(
                    experience_context=PayPalWalletExperienceContext(
                        shipping_preference=ShippingPreference.NO_SHIPPING,
                        return_url=return_url,
                        cancel_url=cancel_url,
                        brand_name='Neige Investments PTY Limited',
                        user_action=PayPalExperienceUserAction.PAY_NOW,
                        # payment_method_preference=PayeePaymentMethodPreference.UNRESTRICTED,
                    )
                )
            )
        ),
        # 'paypal_request_id': request_id,
        'prefer': 'return=minimal'
    }
    try:
        result = orders_controller.orders_create(collect)
        response_data = json.loads(result.text)
        response_data['return_url'] = return_url
        response_data['cancel_url'] = cancel_url
        return JsonResponse(response_data)
    except ErrorException as e:
        return JsonResponse({'error': e.message}, status=e.response_code)
    except APIException as e:
        return JsonResponse({'error': e.reason}, status=e.response_code)


def capture_booking_order(request):
    order_id = json.loads(request.body)['orderID']
    orders_controller = client.orders
    collect = {
        'id': order_id,
        # 'paypal_request_id': request_id,
        'prefer': 'return=minimal'
    }
    try:
        result = orders_controller.orders_capture(collect)
        response_data = json.loads(result.text)
        booking_id = response_data['purchase_units'][0]['payments']['captures'][0]['custom_id']  # booking id associated with capture
        transaction_id = response_data['purchase_units'][0]['payments']['captures'][0]['id']
        booking = BookingRecord.objects.get(id=booking_id)
        booking.update_payment_status(BookingRecord.BookingRecordPaymentStatus.PAID, transaction_id=transaction_id)
        booking.update_status(BookingRecord.BookingRecordStatus.FINALISED)
        booking.send_confirmation_email()
        return JsonResponse(response_data)
    except ErrorException as e:
        return JsonResponse({'error': e.message}, status=e.response_code)
    except APIException as e:
        return JsonResponse({'error': e.reason}, status=e.response_code)
