from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
import requests
import os

from models import db, connect_db, User, CoinbaseExchangeAuth, Account, Deposit, Currency
from forms import UserAddForm, LoginForm, DepositForm, AllocationForm, PortfolioForm

from helpers.helpers import user_accounts_to_db, payment_methods_to_db, handle_deposit

app = Flask(__name__, instance_path='/instance')

app.config.from_pyfile('instance/config.py')
debug = DebugToolbarExtension(app)

connect_db(app)
db.create_all()

API_URL = "https://api-public.sandbox.pro.coinbase.com/"

API_KEY = app.config["API_KEY"]
API_SECRET = app.config["API_SECRET"]
API_PASSPHRASE = app.config["API_PASSPHRASE"]

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
    accounts = user_accounts_to_db(user_id, auth)

    return render_template("users/dashboard.html", accounts=accounts)


@app.route('/users/<int:user_id>/deposit', methods=["GET", "POST"])
def deposit(user_id):
    """Deposit funds into Coinbase Pro."""
    # if not g.user:
    #     flash("Access unauthorized.", "danger")
    #     return redirect("/")
    form = DepositForm()

    # get payment methods from coinbase and put in db
    payment_methods = payment_methods_to_db(user_id, "USD", auth)

    form.payment_method.choices = [(key, val)
                                   for key, val in payment_methods.items()]

    if form.validate_on_submit():
        payment_method_id = form.payment_method.data
        amount = form.amount.data
        currency = "USD"

        data = handle_deposit(user_id, auth, amount,
                              currency, payment_method_id)

        if data:
            flash("Deposit initiated!", "success")
    return render_template("users/deposit.html", form=form)


@app.route('/users/<int:user_id>/portfolio', methods=["GET", "POST"])
def allocations(user_id):
    """View and set allocations for a user's portfolio of currencies."""
    # if not g.user:
    #     flash("Access unauthorized.", "danger")
    #     return redirect("/")
    form = PortfolioForm()

    # get all available account currencies for this user
    user = User.query.get(user_id)
    currencies = [account.currency for account in user.accounts]

    for currency in currencies:
        allocation_form = AllocationForm()
        allocation_form.currency = currency
        allocation_form.percentage = 0

        form.portfolio.append_entry(allocation_form)

    return render_template('/users/portfolio.html', form=form)

##############################################################################
# Currency pages


@app.route('/currencies/<string:currency>')
def currency(currency):
    """Show currency info."""

    response = requests.get(f"{API_URL}products/{currency}-btc/ticker")
    data = response.json()
    return render_template(f"currencies/currency.html", currency=currency, data=data)


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
