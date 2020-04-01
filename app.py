from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
import requests
import os

from models import db, connect_db, User, CoinbaseExchangeAuth, Account
from forms import UserAddForm, LoginForm, DepositForm

from helpers.helpers import update_user_accounts, payment_methods_to_db

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

    response = requests.get(API_URL + 'accounts', auth=auth)
    accounts = response.json()

    # update the user's accounts in the db
    update_user_accounts(accounts)

    return render_template("users/dashboard.html", accounts=accounts)


@app.route('/users/<int:user_id>/deposit')
def deposit(user_id):
    """Deposit funds into Coinbase Pro."""
    # if not g.user:
    #     flash("Access unauthorized.", "danger")
    #     return redirect("/")
    form = DepositForm()
    payment_methods = payment_methods_to_db(user_id, "USD", auth)

    form.payment_method.choices = [(key, val)
                                   for key, val in payment_methods.items()]

    return render_template("users/deposit.html", form=form)


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
