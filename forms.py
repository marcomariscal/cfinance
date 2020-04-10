from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, DecimalField, FieldList, FormField, IntegerField, HiddenField
from wtforms.validators import DataRequired, InputRequired, Required


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


class TargetAllocationForm(FlaskForm):
    """Allocations form."""
    class Meta:
        csrf = False

    currency = HiddenField('Currency')
    percentage = DecimalField('%', validators=[InputRequired()], places=0)


class PortfolioForm(FlaskForm):
    """Portfolio is a representation of all target allocations for a user."""
    portfolio = FieldList(FormField(TargetAllocationForm),
                          validators=[Required()])

    def validate(self):
        if self.request == 'POST':
            return True


class OrderForm(FlaskForm):
    """Make a trade on Coinbase Pro."""
    product_id = SelectField(
        'From Currency', choices=[], validators=[InputRequired()])

    side = SelectField(
        'Side', choices=[('buy', 'Buy'), ('sell', 'Sell')])

    funds = DecimalField('Amount in From Currency',
                         validators=[DataRequired(message="Valid input required.")])
