from models import db, Account, PaymentMethod, User, CurrentAllocation, TargetAllocation
import requests
import os
from instance.config import CMC_PRO_API_KEY
import simplejson as json
import pandas as pd
import numpy as np


API_URL = "https://api-public.sandbox.pro.coinbase.com/"
COINGECKO_API_URL = 'https://api.coingecko.com/api/v3/'

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

        # don't include LINK becuase you can't transact with it in the sandbox
        if currency not in ['LINK', 'EUR', 'GBP']:
            try:
                balance_usd = convert_currency(
                    currency, balance_native, USD_REFERENCE)

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
    """Update the user's portfolio of assets in the db with what is in CBP."""
    assets = portfolio_pct_allocations(user_id)

    user = User.query.get_or_404(user_id)
    allocations = user.current_allocations

    # delete all rows in model so we can sync the most up to date allocations in CBP
    if len(allocations) > 0:

        db.session.query(CurrentAllocation).delete()
        db.session.commit()

    # create allocations for db if there are no current allocations
    else:
        allocations = []

        for asset, pct in assets.items():
            allocation = CurrentAllocation(
                currency=asset, percentage=pct, user_id=user_id)
            allocations.append(allocation)

        db.session.add_all(allocations)
        db.session.commit()


def update_target_allocations(user_id, target_portfolio):
    """Update the user's target allocations in the db."""

    user = User.query.get_or_404(user_id)
    target_allocations = user.target_allocations

    # delete all rows in model so we can sync the most up to date allocations in CBP
    if len(target_allocations) > 0:

        db.session.query(TargetAllocation).delete()
        db.session.commit()

    # create allocations for db if there are no current allocations
    else:
        targets = []

        for asset in target_portfolio:
            allocation = TargetAllocation(
                currency=asset["currency"], percentage=asset["percentage"], user_id=user_id)
            targets.append(allocation)

        db.session.add_all(targets)
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


def get_product(product_id):
    """Get product (currency) info from Coinbase API."""
    response = requests.get(API_URL + f"products/{product_id}/ticker")
    data = response.json()
    return data


def get_current_price(product_id):
    response = requests.get(API_URL + f"products/{product_id}/ticker")
    data = response.json()

    return data.get('price', 'None')


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


def rebalance_portfolio(user_id, auth):
    """Rebalance a portfolio to the given allocation percentages.
    (i.e.: a portfolio composed of 50% BTC and 50% ETH will be bought according to those percentages, based on how the
    portfolio is currently allocated)

    Portfolio input is a list of currency objects:

        [{"currency": currency, "percentage": percentage}]

    """
    update_user_accounts(user_id, auth)
    update_allocations(user_id)

    user = User.query.get_or_404(user_id)

    currencies = [(account.currency, account.balance_native)
                  for account in user.accounts]

    targets = [(target.currency, target.percentage)
               for target in user.target_allocations]

    targets_df = pd.DataFrame(
        targets, columns=['Currency', 'Target Allocation'])

    df = pd.DataFrame(data=currencies, columns=[
        "Currency", "Balance Native"])

    df = df.merge(targets_df)

    # the tickers we need to use for each currency to transact/place orders
    df["Ticker"] = df["Currency"].map(lambda x: find_ticker(x))

    quote_currencies = df["Ticker"].str.split(pat='-', expand=True)

    df["Quote Currency"] = quote_currencies[1]

    df["Price in Quote"] = df.apply(lambda x: convert_currency(
        x["Currency"], 1, x["Quote Currency"]), axis=1)

    # create column with prices relevant to the ticker (i.e.: 'ETH-BTC' will have a price in 'BTC')
    df["Price in Ticker"] = df["Ticker"].map(lambda x: get_current_price(x))

    df["Price in USD"] = df["Currency"].map(
        lambda x: convert_currency(x, 1, 'USD'))

    df["Total USD Value"] = df["Price in USD"] * df["Balance Native"]

    df["Total USD Value Delta"] = sum(
        df["Total USD Value"]) * df["Target Allocation"] - df["Total USD Value"]

    df["Price in Ticker"] = pd.to_numeric(
        df["Price in Ticker"], errors='coerce')

    df["Total Ticker Value"] = np.where(
        df["Price in Ticker"] is not "NaN", df["Price in Ticker"] * df["Balance Native"], df["Balance Native"])

    btc_usd_price = df.loc[df["Currency"] == 'BTC']["Price in Ticker"].to_list()[
        0]

    df["Delta Ticker Amount"] = np.where(df["Ticker"] != 'ETH-BTC', df["Total USD Value Delta"] /
                                         df["Price in USD"] * df["Price in Ticker"], df["Total USD Value Delta"] / btc_usd_price)

    df["Delta Quote Amount"] = np.where(df["Ticker"] != 'ETH-BTC', df["Total USD Value Delta"] / df["Price in USD"] *
                                        df["Price in Quote"], df["Total USD Value Delta"] / btc_usd_price)

    df["Delta Ticker Amount"] = df["Delta Ticker Amount"].map(
        lambda x: round(x, 2))

    df["Weight"] = np.where(df["Delta Ticker Amount"] >
                            0, 'underweight', 'overweight')

    df["Side"] = np.where(df["Weight"] == 'overweight', 'sell', 'buy')

    df["Amount Available to Trade"] = df["Quote Currency"].map(lambda x: [
        account.balance_native for account in user.accounts if account.currency == x])

    # create a df for placing orders
    order_df = df[['Currency', 'Ticker', 'Delta Quote Amount',
                   'Weight', 'Side', 'Amount Available to Trade', 'Total Ticker Value', 'Balance Native']]

    for index, row in order_df.iterrows():

        currency = row["Currency"]
        ticker = row["Ticker"]
        weight = row["Weight"]
        side = row["Side"]
        delta = round(row["Delta Quote Amount"], 2)
        delta = abs(delta)
        current_ticker_val = row["Total Ticker Value"]
        amount_avail_to_trade = round(row["Amount Available to Trade"][0], 2) if len(
            row["Amount Available to Trade"]) != 0 else row["Balance Native"]

        print("###################")
        print("currency:", currency, "current val:", current_ticker_val,
              'amount:', amount_avail_to_trade, 'delta:', delta, 'weight:', weight)

        # # is the delta between our current and target too large, if yes then we continue placing trades
        # if delta > .01:
        # check for overweight currencies first and sell them at the delta amount
        if weight == 'overweight' and currency not in ['USD', 'USDC']:

            order = place_order(user_id, auth, 'sell', delta, ticker)

            # if 'funds is too large' in order["message"]:
            #     order = place_order(
            #         user_id, auth, 'sell', delta / 2, ticker)

            print("###################")
            print(order)
            # move on to next currency
            continue

        # check for underweight currencies and check if there is amount available to trade
        if weight == 'underweight' and 0 < delta < amount_avail_to_trade:
            order = place_order(user_id, auth, 'buy',
                                delta, ticker)
            print("###################")
            print(order)
            # move on to next currency
            continue

        # check if we are currently at USDC and USDC is underweight, if so, convert USD to USDC
        if currency == 'USD' and weight == 'overweight':
            conversion = stablecoin_conversion(auth, 'USD', 'USDC', delta)
            print("###################")
            print(conversion)

        # check if we are currently at USDC and USDC is underweight, if so, convert USD to USDC
        if currency == 'USDC' and weight == 'overweight':
            conversion = stablecoin_conversion(auth, 'USDC', 'USD', delta)
            print("###################")
            print(conversion)

        if currency == 'USD' and weight == 'underweight':
            conversion = stablecoin_conversion(auth, 'USDC', 'USD', delta)
            print("###################")
            print(conversion)

        if currency == 'USDC' and weight == 'underweight':
            conversion = stablecoin_conversion(auth, 'USD', 'USDC', delta)
            print("###################")
            print(conversion)
        #  # check if we are currently at USDC and USDC is underweight, if so, convert USD to USDC
        # if currency == 'USDC' and weight == 'overweight':
        #     conversion = stablecoin_conversion(auth, 'USDC', 'USD', delta)
        #     print("###################")
        #     print(conversion)

    update_user_accounts(user_id, auth)
    update_allocations(user_id)


def find_ticker(curr):
    """Find relevant ticker (used for placing orders) for a currency."""
    products = get_products()

    potential_tickers = [f'{curr}-USD', f'{curr}-USDC', f'{curr}-BTC']

    for ticker in potential_tickers:
        # find the first relevant ticker match within the accessible products
        if ticker in products:
            return ticker


def stablecoin_conversion(auth, from_currency, to_currency, amount):
    """Convert stablecoin to fiat and vice versa (i.e.: convert USD to USDC)."""

    params = {
        "from": from_currency,
        "to": to_currency,
        "amount": amount
    }

    response = requests.post(
        API_URL + 'conversions', data=json.dumps(params), auth=auth)

    data = response.json()
    return data


def convert_currency(from_currency, amount, to_currency='usd'):

    try:
        to_currency = to_currency.lower()
    except AttributeError as e:
        print(e)

    if from_currency == 'BTC':
        from_curr = 'bitcoin'

    if from_currency == 'ETH':
        from_curr = 'ethereum'

    if from_currency == 'BAT':
        from_curr = 'basic attention token'

    if from_currency == 'BAT':
        from_curr = 'basic-attention-token'

    if from_currency == 'USDC':
        return amount

    if from_currency == 'USD':
        return amount

    # change to currency for compatability
    if to_currency == 'BTC':
        to_currency = 'bitcoin'

    if to_currency == 'ETH':
        to_currency = 'ethereum'

    if to_currency == 'BAT':
        to_currency = 'basic attention token'

    if to_currency == 'BAT':
        to_currency = 'basic-attention-token'

    if to_currency == 'USDC' or 'usdc':
        to_currency = 'usd'

    if to_currency == 'USD':
        to_currency = 'usd'

    params = {
        "ids": from_curr,
        "vs_currencies": to_currency
    }

    headers = {
        'Accepts': 'application/json',
    }

    if from_currency not in ['USDC', 'USD']:
        response = requests.get(
            COINGECKO_API_URL + 'simple/price', params=params, headers=headers)

        json = response.json()
        data = json[from_curr]
        price = data[to_currency]

        converted_amount = float(price) * float(amount)

    return converted_amount
