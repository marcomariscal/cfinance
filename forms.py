from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired


class UserAddForm(FlaskForm):
    """Form for adding users."""

    api_key = StringField('Coinbase Pro API Key', validators=[DataRequired()])
    api_secret = PasswordField(
        'Coinbase Pro API Secret Key', validators=[DataRequired()])
    api_passphrase = PasswordField(
        'Coinbase Pro API Secret Passphrase', validators=[DataRequired()])


class LoginForm(FlaskForm):
    """Login form."""

    api_key = StringField('Coinbase Pro API Key', validators=[DataRequired()])
    api_secret = PasswordField(
        'Coinbase Pro API Secret Key', validators=[DataRequired()])
    api_passphrase = PasswordField(
        'Coinbase Pro API Secret Passphrase', validators=[DataRequired()])


class DepositForm(FlaskForm):
    """Deposit form."""
    amount = StringField('Amount', validators=[DataRequired()])
    currency = StringField(
        'Currency', validators=[DataRequired()])
    payment_method = StringField(
        'Payment Method', validators=[DataRequired()])
