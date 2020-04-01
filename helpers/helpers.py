from models import Account, PaymentMethod, db
import requests

API_URL = "https://api-public.sandbox.pro.coinbase.com/"


def update_user_accounts(accounts):
    for account in accounts:
        id = account["id"]
        account_in_db = Account.query.get(id)

        if account_in_db:
            account_in_db.currency = account["currency"]
            account_in_db.balance = account["balance"]
            account_in_db.available = account["available"]
            account_in_db.hold = account["hold"]
            db.session.add(account_in_db)

        else:
            currency = account["currency"]
            balance = account["balance"]
            available = account["available"]
            hold = account["hold"]

            account = Account(id=id, currency=currency,
                              balance=balance, available=available, hold=hold, user_id=user_id)

            db.session.add(account)

    db.session.commit()


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
