from flask import Flask, render_template, request, flash, redirect, session, g, jsonify, url_for
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
import requests
import os

from models import db, connect_db, User, CoinbaseExchangeAuth, Account, Deposit, Currency
from forms import UserAddForm, LoginForm, DepositForm, AllocationForm, PortfolioForm, OrderForm

from helpers.helpers import *

app = Flask(__name__, instance_path='/instance')

app.config.from_pyfile('instance/config.py')
debug = DebugToolbarExtension(app)

connect_db(app)
db.create_all()

API_URL = "https://api-public.sandbox.pro.coinbase.com/"

API_KEY = app.config["API_KEY"]
API_SECRET = app.config["API_SECRET"]
API_PASSPHRASE = app.config["API_PASSPHRASE"]

CMC_PRO_API_KEY = app.config["CMC_PRO_API_KEY"]


auth = CoinbaseExchangeAuth(API_KEY, API_SECRET, API_PASSPHRASE)

CURR_USER_KEY = "curr_user"

##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def update_user_info(user_id):
    update_user_accounts(user_id, auth)
    update_allocations(user_id)


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to user's dashboard.

    If form not valid, present form.

    If the user can't be authed within Coinbase, flash message
    and re-present form.
    """
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                api_key=form.api_key.data,
                api_secret=form.api_secret.data,
                api_passphrase=form.api_passphrase.data,
            )
            db.session.commit()

        except IntegrityError as e:
            flash("Unable to authorize access to Coinbase Pro", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect(f"/users/{user.id}/dashboard")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(api_key=form.api_key.data, api_secret=form.api_secret.data,
                                 api_passphrase=form.api_passphrase.data)

        if user:
            do_login(user)
            flash(f"Welcome Back!", "success")
            return redirect(f"/users/{user.id}/dashboard")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    do_logout()

    flash("You have successfully logged out.", 'success')
    return redirect("/login")


##############################################################################
# User pages
@app.route('/users/<int:user_id>/dashboard')
def dashboard(user_id):
    """Show user's dashboard."""

    # if not g.user:
    #     flash("Access unauthorized.", "danger")
    #     return redirect("/")

    # update the user's accounts in the db and return the accounts
    update_user_info(user_id)

    user = User.query.get(user_id)
    accounts = user.accounts
    total_balance = total_balance_usd(user_id)

    portfolio = portfolio_pct_allocations(user_id)

    return render_template("users/dashboard.html", user=user, accounts=accounts, total_balance=total_balance, portfolio=portfolio)


@app.route('/users/<int:user_id>/deposit', methods=["GET", "POST"])
def deposit(user_id):
    """Deposit funds into Coinbase Pro."""
    # if not g.user:
    #     flash("Access unauthorized.", "danger")
    #     return redirect("/")

    user = User.query.get(user_id)

    form = DepositForm()

    # get payment methods from coinbase and put in db
    update_payment_methods(user_id, "USD", auth)

    # get payment methods from db
    form.payment_method.choices = [(method.id, method.name)
                                   for method in user.payment_methods]

    if form.validate_on_submit():
        payment_method_id = form.payment_method.data
        amount = form.amount.data
        currency = "USD"

        res = handle_deposit(user_id, auth, amount,
                             currency, payment_method_id)
        redirect('/')
        flash("Deposit initiated!", "success")
    return render_template("users/deposit.html", form=form)


@app.route('/users/<int:user_id>/rebalance', methods=["GET", "POST"])
def rebalance(user_id):
    """View and set allocations for a user's portfolio of currencies."""
    # if not g.user:
    #     flash("Access unauthorized.", "danger")
    #     return redirect("/")
    form = PortfolioForm()

    # get all available account currencies for this user
    assets = portfolio_pct_allocations(user_id)
    assets = assets.items()

    for asset, pct in assets:
        allocation_form = AllocationForm()
        allocation_form.currency = asset
        allocation_form.percentage = pct * 100

        form.portfolio.append_entry(allocation_form)

    if form.validate_on_submit():
        flash('Rebalance Initiated')
        redirect(url_for(dashboard, user_id=user_id))

    return render_template('/users/rebalance.html', form=form, assets=assets)


@app.route('/users/<int:user_id>/trade', methods=['GET', 'POST'])
def trade(user_id):
    user = User.query.get(user_id)

    valid_products = get_valid_products_for_orders(user.accounts)
    form = OrderForm()
    form.product_id.choices = [(prod, prod) for prod in valid_products]

    if form.validate_on_submit():

        product_id = form.product_id.data
        side = form.side.data

        # funds are the amount of funds in the quote currency (from currency) that will
        # be used to buy the "to_currency"
        funds = form.funds.data

        data = place_order(user_id, auth, side, funds, product_id)

        if data:
            flash('Your order was placed', f'{data}')
            # redirect(f'/{user_id}/trade')

    return render_template('users/trade.html', form=form)


##############################################################################
# Routes for the front end
@app.route('/api/users/<int:user_id>/portfolio_pcts', methods=['GET'])
def get_portfolio_pct_allocations(user_id):
    pct_allocations = portfolio_pct_allocations(user_id)

    return jsonify(pct_allocations), 200


##############################################################################
# Currency pages
@app.route('/currencies/<string:currency>')
def currency(currency):
    """Show currency info."""

    response = requests.get(f"{API_URL}products/{currency}-btc/ticker")
    data = response.json()

    convert_to_usd = convert_currency(currency, 'usd', 1)
    return render_template(f"currencies/currency.html", currency=currency, data=data, usd=convert_to_usd)


##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage."""

    if g.user:
        return render_template('home.html')

    else:
        return render_template('home-anon.html')


@app.errorhandler(404)
def page_not_found(e):
    """404 NOT FOUND page."""

    return render_template('404.html'), 404
