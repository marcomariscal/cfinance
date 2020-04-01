from models import Account, PaymentMethod, db
import requests

API_URL = "https://api-public.sandbox.pro.coinbase.com/"


def user_accounts_to_db(user_id, auth):
    response = requests.get(API_URL + 'accounts', auth=auth)
    accounts = response.json()

    for acct in accounts:
        id = acct["id"]
        account = Account.query.get(id)

        if account:
            account.currency = acct["currency"]
            account.balance = acct["balance"]
            account.available = acct["available"]
            account.hold = acct["hold"]
            db.session.add(account)

        else:
            currency = acct["currency"]
            balance = acct["balance"]
            available = acct["available"]
            hold = acct["hold"]

            account = Account(id=id, currency=currency,
                              balance=balance, available=available, hold=hold, user_id=user_id)
            db.session.add(account)

    db.session.commit()
    return accounts


def payment_methods_to_db(user_id, currency, auth):
    """Get payment methods from Coinbase Pro user for a specified currency."""

    response = requests.get(API_URL + "payment-methods", auth=auth)
    data = response.json()

    payment_methods = {}

    for method in data:
        if method["currency"] == currency:
            id = method["id"]
            # get the methods name so we can use it in a form
            name = method["name"]

            payment_methods[id] = name

            payment_method = PaymentMethod.query.get(id)

            if payment_method:
                payment_method.name = name
                payment_method.user_id = user_id
            else:
                payment_method = PaymentMethod(
                    id=id, name=method["name"], user_id=user_id)

            db.session.add(payment_method)
        db.session.commit()

    return payment_methods


def handle_deposit(user_id, auth, amount, currency, payment_method_id):
    """Deposit funds using user's inputted values and sending to Coinbase API. 
    Can only deposit funds using USD payment methods for now."""
    data = {"amount": amount, "currency": currency,
            "payment_method_id": payment_method_id}

    response = requests.get(
        API_URL + "desposits/payment-methods", data=data, auth=auth)
    json = response.json()

    return json


def get_currencies():
    """Get currencies from Coinbase API."""
    response = requests.get(API_URL + "currencies")
    json = response.json()
    return json
