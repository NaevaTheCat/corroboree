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
            log_headers=True
        )
    )
)


def create_order(cost, billing_reference, return_url, cancel_url):
    """Create a paypal order, returns a json response as: https://developer.paypal.com/docs/api/orders/v2/#orders_create"""
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
                    invoice_id=billing_reference,
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
                        user_action=PayPalExperienceUserAction.PAY_NOW
                    )
                )
            )
        ),
        # 'paypal_request_id': request_id,
        'prefer': 'return=minimal'
    }
    try:
        result = orders_controller.orders_create(collect)
        return result
    except ErrorException as e:
        print(e)
    except APIException as e:
        print(e)


def capture_order(order_id):
    orders_controller = client.orders
    collect = {
        'id': order_id,
        # 'paypal_request_id': request_id,
        'prefer': 'return=minimal'
    }
    try:
        result = orders_controller.orders_capture(collect)
        return result
    except ErrorException as e:
        print(e)
    except APIException as e:
        print(e)
