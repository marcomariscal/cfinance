from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
import json
import hmac
import hashlib
import time
import requests
import base64
from requests.auth import AuthBase

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

    def __repr__(self):
        return f"<User #{self.id}: {self.api_key}>"

    @classmethod
    def signup(cls, api_key, api_secret, api_passphrase):
        """Sign up user using coinbase pro api key, username, and password.

        First must check that the credentials provided actually exist in Coinbase and are
        authenticated with the custom Coinbase auth class.

        Then we hash api_key, secret, and passphrase and add user to system.
        """

        coinbase_auth = CoinbaseExchangeAuth(
            api_key, api_secret, api_passphrase)

        if coinbase_auth:

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

    currency = db.Column(db.String,
                         nullable=False)

    balance = db.Column(db.Float,
                        nullable=False)

    available = db.Column(db.Float, nullable=False)

    hold = db.Column(db.Float, nullable=False)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
    )

    user = db.relationship('User')


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

    user = db.relationship('User')


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


def connect_db(app):
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """

    db.app = app
    db.init_app(app)
