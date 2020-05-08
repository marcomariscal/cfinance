from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask import g
import json
import hmac
import hashlib
import time
import requests
import base64
from requests.auth import AuthBase
from binascii import Error


bcrypt = Bcrypt()
db = SQLAlchemy()


class User(db.Model):
    """User."""

    __tablename__ = "users"

    id = db.Column(db.Integer,
                   primary_key=True)

    api_key = db.Column(db.String,
                        nullable=False, unique=True)

    api_secret = db.Column(db.String,
                           nullable=False)

    api_passphrase = db.Column(db.String, nullable=False)

    accounts = db.relationship('Account',
                               backref='user')

    payment_methods = db.relationship('PaymentMethod',
                                      backref='user')

    target_allocations = db.relationship('TargetAllocation',
                                         backref='user')

    current_allocations = db.relationship('CurrentAllocation',
                                          backref='user')

    auth = db.Column(db.PickleType(), nullable=True)

    # try to initialize the user with an attribute holding the coinbase pro authentication
    def __init__(self, api_key, api_secret, api_passphrase):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase

    def __repr__(self):
        return f"<User #{self.id}: {self.api_key}>"

    def set_auth(self, api_key, api_secret, api_passphrase):
        cb_auth = CoinbaseExchangeAuth(api_key, api_secret, api_passphrase)

        self.auth = cb_auth

    @classmethod
    def signup(cls, api_key, api_secret, api_passphrase):
        """Sign up user using coinbase pro api key, username, and password.

        First must check that the credentials provided actually exist in Coinbase and are
        authenticated with the custom Coinbase auth class.

        Then we hash api_key, secret, and passphrase and add user to system.
        """

        coinbase_auth = CoinbaseExchangeAuth(
            api_key, api_secret, api_passphrase)

        # test the auth to see if valid user exists in CBP
        is_auth = CoinbaseExchangeAuth.test_auth(coinbase_auth)

        if is_auth:

            hashed_secret = bcrypt.generate_password_hash(
                api_secret).decode('UTF-8')
            hashed_passphrase = bcrypt.generate_password_hash(
                api_passphrase).decode('UTF-8')

            user = User(
                api_key=api_key,
                api_secret=hashed_secret,
                api_passphrase=hashed_passphrase
            )

            db.session.add(user)
            return user

        return False

    @classmethod
    def authenticate(cls, api_key, api_secret, api_passphrase):
        """Find user with coinbase pro credentials`.

        This is a class method (call it on the class, not an individual user.)
        It searches for a user whose password hash matches this password
        and, if it finds such a user, returns that user object.

        If can't find matching user (or if creds are wrong), returns False.
        """

        user = cls.query.filter_by(api_key=api_key).first()

        if user:

            is_auth_api_secret = bcrypt.check_password_hash(
                user.api_secret, api_secret)
            is_auth_api_passphrase = bcrypt.check_password_hash(
                user.api_passphrase, api_passphrase)

            if is_auth_api_secret and is_auth_api_passphrase:

                return user

        return False


class Account(db.Model):
    """Accounts for the user in coinbase, related to how much balance/funding they have for each currency."""

    __tablename__ = "accounts"

    id = db.Column(db.String,
                   primary_key=True)

    currency = db.Column(db.String, nullable=False)

    balance_native = db.Column(db.Float,
                               nullable=False)

    balance_usd = db.Column(db.Float,
                            nullable=False)

    available = db.Column(db.Float, nullable=False)

    hold = db.Column(db.Float, nullable=False)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
    )


class PaymentMethod(db.Model):
    """Payment methods for a user."""

    __tablename__ = "payment_methods"

    id = db.Column(db.String,
                   primary_key=True)

    name = db.Column(db.String,
                     nullable=False)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
    )


class Deposit(db.Model):
    """Deposit instance for a user."""

    __tablename__ = "deposits"

    id = db.Column(db.String,
                   primary_key=True)

    amount = db.Column(db.Float,
                       nullable=False)

    currency = db.Column(db.String, db.ForeignKey(
        'currencies.name'), nullable=False)

    payment_method_id = db.Column(
        db.String,
        db.ForeignKey('payment_methods.id'),
        nullable=False,
    )

    payout_at = db.Column(db.DateTime, nullable=False)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
    )

    user = db.relationship('User')
    payment_method = db.relationship('PaymentMethod')


class Currency(db.Model):
    """Available currencies from Coinbase Pro API."""

    __tablename__ = "currencies"

    name = db.Column(db.String, primary_key=True,
                     nullable=False)


class TargetAllocation(db.Model):
    """Target allocation percentages per currency for a user."""

    __tablename__ = "target_allocations"

    currency = db.Column(db.String, primary_key=True,
                         nullable=False)

    percentage = db.Column(db.Float,
                           nullable=False)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
    )


class CurrentAllocation(db.Model):
    """Current allocation percentages per currency for a user."""

    __tablename__ = "current_allocations"

    currency = db.Column(db.String, primary_key=True,
                         nullable=False)

    percentage = db.Column(db.Float,
                           nullable=False)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
    )

# Create custom authentication for Exchange


class CoinbaseExchangeAuth(AuthBase):
    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

    def __call__(self, request):
        timestamp = str(time.time())
        message = timestamp + request.method + \
            request.path_url + (request.body or '')
        hmac_key = base64.b64decode(self.secret_key)
        signature = hmac.new(hmac_key, message.encode(), hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest()).decode()

        request.headers.update({
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        })
        return request

    @classmethod
    def test_auth(cls, auth):
        """Test the auth with an API call to validate that a user exists in Coinbase Pro."""
        try:
            r = requests.get(g.api_url + 'accounts', auth=auth)
            data = r.json()

            # check that the first account has an Id, signifying that it exists
            if data and r.status_code == 200:
                return True

        except Error:
            return False

        return False


def connect_db(app):
    """Connect the database to Flask app."""

    db.app = app
    db.init_app(app)
