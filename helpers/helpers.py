from models import Account, PaymentMethod, db, User, Portfolio, Allocation
import requests
import os
from instance.config import CMC_PRO_API_KEY
import simplejson as json


API_URL = "https://api-public.sandbox.pro.coinbase.com/"
COINMARKETCAP_API_URL = 'https://pro-api.coinmarketcap.com/v1/'

# used for converting currencies from native to USD
USD_REFERENCE = 'usd'


def update_user_accounts(user_id, auth):
    response = requests.get(API_URL + 'accounts', auth=auth)
    accounts = response.json()

    for account in accounts:
        id = account["id"]
        currency = account["currency"]
        balance_native = account["balance"]
        available = account["available"]
        hold = account["hold"]

        try:
            balance_usd = convert_currency(
                currency, USD_REFERENCE, balance_native)

            account_in_db = Account.query.get(id)

            if account_in_db:
                account_in_db.currency = currency
                account_in_db.balance_native = balance_native
                account_in_db.balance_usd = balance_usd
                account_in_db.available = available
                account_in_db.hold = hold

                db.session.add(account_in_db)

            else:
                account = Account(id=id, currency=currency,
                                  balance_native=balance_native,
                                  balance_usd=balance_usd,
                                  available=available, hold=hold, user_id=user_id)

                db.session.add(account)
        except KeyError:
            pass

    db.session.commit()


def update_payment_methods(user_id, currency, auth):
    """Get payment methods from Coinbase Pro user for a specified currency."""

    response = requests.get(API_URL + "payment-methods", auth=auth)
    data = response.json()

    for method in data:
        if method["currency"] == currency:
            id = method["id"]
            # get the methods name so we can use it in a form
            name = method["name"]

            payment_method = PaymentMethod.query.get(id)

            if payment_method:
                payment_method.name = name
                payment_method.user_id = user_id
            else:
                payment_method = PaymentMethod(
                    id=id, name=method["name"], user_id=user_id)

            db.session.add(payment_method)
        db.session.commit()


def update_allocations(user_id):
    """Update the user's portoflio of assets in the db."""
    assets = portfolio_pct_allocations(user_id)

    allocations = []
    # make allocations for db
    for asset, pct in assets.items():
        allocation = Allocation(
            currency=asset, percentage=pct, user_id=user_id)
        allocations.append(allocation)

    db.session.add_all(allocations)
    db.session.commit()


def handle_deposit(user_id, auth, amount, currency, payment_method_id):
    """Deposit funds using user's inputted values and sending to Coinbase API.
    Can only deposit funds using USD payment methods for now."""
    params = {
        "amount": amount,
        "currency": currency,
        "payment_method_id": payment_method_id
    }

    response = requests.post(
        API_URL + 'deposits/payment-method', data=json.dumps(params), auth=auth)

    data = response.json()

    return data


def get_currencies():
    """Get currencies from Coinbase API."""
    response = requests.get(API_URL + "currencies")
    json = response.json()
    return json


def get_asset_allocation_percentages(user_id):
    user = User.query.get(user_id)


def convert_currency(from_currency, to_currency, amount):
    """Convert a currency amount to different currency."""

    to_currency = to_currency.upper()
    params = {
        "symbol": from_currency,
        "amount": amount,
        "convert": to_currency
    }

    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': CMC_PRO_API_KEY
    }

    response = requests.get(
        COINMARKETCAP_API_URL + 'tools/price-conversion', params=params, headers=headers)
    json = response.json()
    data = json["data"]
    to_amount = round(data["quote"][to_currency]['price'], 2)

    return to_amount


def total_balance_usd(user_id):
    user = User.query.get(user_id)
    accounts = user.accounts
    total_usd_balance = sum([account.balance_usd for account in accounts])

    return total_usd_balance


def portfolio_pct_allocations(user_id):
    user = User.query.get(user_id)
    accounts = user.accounts

    total = total_balance_usd(user_id)

    pct_allocations = {
        account.currency: account.balance_usd / total for account in accounts}

    return pct_allocations


def place_order(user_id, auth, side, funds, product_id):
    params = {'product_id': product_id,
              'side': side,
              'type': 'market',
              'funds': funds}

    response = requests.post(
        API_URL + 'orders', data=json.dumps(params), auth=auth)

    data = response.json()
    return data


def get_products():
    """Get available products from Coinbase API."""
    response = requests.get(API_URL + "products")
    data = response.json()
    avail_prods = [prod["id"] for prod in data]
    return avail_prods


def get_valid_products_for_orders(accounts):
    """Use the available products from CB and look up against user's accounts
    to find products that are actually tradeable.

    Returns available base and quote (to and from, respectively) currencies."""

    accounts = [account.currency for account in accounts]
    avail_prods = get_products()

    valid_prods = set([
        prod for prod in avail_prods
        if prod.split('-')[1] in accounts])

    return valid_prods
