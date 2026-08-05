import base64

import requests
from decouple import config

PAYPAL_CLIENT_ID = config("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = config("PAYPAL_CLIENT_SECRET")


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


def create_order(amount):

    token = get_access_token()["access_token"]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    body = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    "value": str(amount),
                }
            }
        ]
    }

    response = requests.post(
        "https://api-m.sandbox.paypal.com/v2/checkout/orders",
        headers=headers,
        json=body,
    )

    return response.json()

def capture_order(order_id):

    token = get_access_token()["access_token"]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    response = requests.post(
        f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture",
        headers=headers,
    )

    return response.json()