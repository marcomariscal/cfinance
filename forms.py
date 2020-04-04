from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, DecimalField, FieldList, FormField
from wtforms.validators import DataRequired, InputRequired


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
    payment_method = SelectField(
        'Payment Method', choices=[], validators=[InputRequired()])
    amount = DecimalField('Amount in USD', validators=[DataRequired()])


class AllocationForm(FlaskForm):
    """Allocations form."""
    currency = StringField(
        'Currency', validators=[DataRequired()])
    percentage = DecimalField('%', validators=[DataRequired()])


class PortfolioForm(FlaskForm):
    """Portfolio is a representation of all allocations for a user."""
    portfolio = FieldList(FormField(AllocationForm))


class OrderForm(FlaskForm):
    """Make a trade on Coinbase Pro."""
    product_id = SelectField(
        'From Currency', choices=[], validators=[InputRequired()])

    side = SelectField(
        'Side', choices=[('buy', 'Buy'), ('sell', 'Sell')])

    funds = DecimalField('Amount in From Currency',
                         validators=[DataRequired(message="Valid input required.")])
