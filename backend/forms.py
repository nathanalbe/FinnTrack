from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FloatField, IntegerField, DateField
from wtforms.validators import DataRequired, Length, Email, EqualTo

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class BudgetForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    submit = SubmitField('Add Budget')

class SpendingForm(FlaskForm):
    description = StringField('Description', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    submit = SubmitField('Add Spending')

class UpdateBudgetForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    submit = SubmitField('Update Budget')

class UpdateSpendingForm(FlaskForm):
    description = StringField('Description', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    submit = SubmitField('Update Spending')
    
class StockSearchForm(FlaskForm):
    symbol = StringField('Stock Symbol', validators=[DataRequired(), Length(min=1, max=10)])
    submit = SubmitField('Search')

class InvestmentForm(FlaskForm):
    symbol = StringField('Stock Symbol', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    purchase_price = FloatField('Purchase Price', validators=[DataRequired()])
    purchase_date = DateField('Purchase Date', validators=[DataRequired()])
    submit = SubmitField('Add Investment')

