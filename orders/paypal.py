import base64
from decimal import ROUND_HALF_UP, Decimal

import requests
from decouple import config

PAYPAL_CLIENT_ID = config("PAYPAL_CLIENT_ID").strip() 
PAYPAL_CLIENT_SECRET = config("PAYPAL_CLIENT_SECRET").strip() 


def format_paypal_amount(amount):
    return str(Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def get_access_token():

    auth = base64.b64encode(
        f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode()
    ).decode()

    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "client_credentials"
    }

    response = requests.post(
        "https://api-m.sandbox.paypal.com/v1/oauth2/token",
        headers=headers,
        data=data,
    )

    return response.json()


def create_order(amount, return_url=None, cancel_url=None):

    token = get_access_token()["access_token"]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    # NOTE: `application_context` (previously used here) is deprecated by
    # PayPal in favor of `payment_source.paypal.experience_context`. More
    # importantly, PayPal's own docs state that omitting `return_url` /
    # `cancel_url` on the order is what produces the
    # "Things don't appear to be working at the moment" error after the
    # buyer approves the payment, because the SDK's in-context popup flow
    # has nowhere to send the buyer back to if it can't complete in place
    # (blocked third-party cookies, popup restrictions, some mobile
    # browsers, etc). We always set them, even though the JS SDK normally
    # intercepts the approval in-context and never actually navigates
    # there, so this is a fallback destination rather than a page the
    # buyer usually sees.
    experience_context = {
        "shipping_preference": "NO_SHIPPING",
        "user_action": "PAY_NOW",
        "return_url": return_url,
        "cancel_url": cancel_url,
    }

    body = {
        "intent": "CAPTURE",
        "payment_source": {
            "paypal": {
                "experience_context": experience_context,
            }
        },
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    "value": format_paypal_amount(amount),
                }
            }
        ],
    }

    response = requests.post(
        "https://api-m.sandbox.paypal.com/v2/checkout/orders",
        headers=headers,
        json=body,
    )
    print("STATUS:", response.status_code)
    print("BODY:", response.text)

    result = response.json()
    if not response.ok:
        result["_http_status"] = response.status_code
    return result

def capture_order(order_id):

    token = get_access_token()["access_token"]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    response = requests.post(
        f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture",
        headers=headers,
        json={},
    )
    print("CAPTURE STATUS:", response.status_code)
    print("CAPTURE BODY:", response.text)

    result = response.json()
    if not response.ok:
        result["_http_status"] = response.status_code
    return result