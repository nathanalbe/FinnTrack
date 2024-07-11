import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_behind_proxy import FlaskBehindProxy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import plaid
from plaid.api import plaid_api
from plaid.model import link_token_create_request, link_token_create_request_user, products, country_code, item_public_token_exchange_request, transactions_get_request, transactions_get_request_options
from plaid.configuration import Configuration
from plaid.exceptions import ApiException
from plaid.api_client import ApiClient
from flask_migrate import Migrate
from alpha_vantage.timeseries import TimeSeries
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import plotly
import plotly.graph_objs as go
import json
from forms import RegistrationForm, LoginForm, BudgetForm, SpendingForm, UpdateBudgetForm, UpdateSpendingForm
from openaibot import get_user_response
from datetime import datetime, timedelta
from dotenv import load_dotenv

import os


app = Flask(__name__, instance_relative_config=True)
app.config['SECRET_KEY'] = '9c7f5ed4fee35fed7a039ddba384397f'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/site.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
proxied = FlaskBehindProxy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

app.config['PLAID_CLIENT_ID'] = os.getenv('PLAID_CLIENT_ID')
app.config['PLAID_SECRET'] = os.getenv('PLAID_SECRET')
app.config['PLAID_ENV'] = os.getenv('PLAID_ENV')  # Change to 'development' or 'production' as needed

app.config['ALPHA_VANTAGE_API_KEY'] = 'your_alpha_vantage_api_key'

# Define your models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    plaid_access_token = db.Column(db.String(200), nullable=True)
    budgets = db.relationship('Budget', backref='owner', lazy=True)
    spendings = db.relationship('Spending', backref='spender', lazy=True)

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return True  # Replace with actual logic as per your application

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)

class Spending(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html')


@app.route("/chat")
@login_required
def chat():
    return render_template('cb.html')

@app.route("/chat", methods=['POST'])
@login_required
def chatting():
    if request.is_json:
        user_msg = request.json.get('message', '')
        bot_msg = get_user_response(user_msg)
        response = {'message': bot_msg}
        return jsonify(response), 200

@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/budget", methods=['GET', 'POST'])
@login_required
def budget():
    form = BudgetForm()
    if form.validate_on_submit():
        budget = Budget(name=form.name.data, amount=form.amount.data, owner=current_user)
        db.session.add(budget)
        db.session.commit()
        flash('Budget added!', 'success')
        return redirect(url_for('budget'))
    budgets = Budget.query.filter_by(owner=current_user)
    return render_template('budget.html', title='Budget', form=form, budgets=budgets)

@app.route("/budget/update/<int:budget_id>", methods=['GET', 'POST'])
@login_required
def update_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    if budget.owner != current_user:
        abort(403)
    form = UpdateBudgetForm()
    if form.validate_on_submit():
        budget.name = form.name.data
        budget.amount = form.amount.data
        db.session.commit()
        flash('Your budget has been updated!', 'success')
        return redirect(url_for('budget'))
    elif request.method == 'GET':
        form.name.data = budget.name
        form.amount.data = budget.amount
    return render_template('update_budget.html', title='Update Budget', form=form)

@app.route("/budget/delete/<int:budget_id>", methods=['POST'])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    if budget.owner != current_user:
        abort(403)
    db.session.delete(budget)
    db.session.commit()
    flash('Your budget has been deleted!', 'success')
    return redirect(url_for('budget'))

@app.route("/spending", methods=['GET', 'POST'])
@login_required
def spending():
    form = SpendingForm()
    if form.validate_on_submit():
        spending = Spending(description=form.description.data, amount=form.amount.data, spender=current_user)
        db.session.add(spending)
        db.session.commit()
        flash('Spending added!', 'success')
        return redirect(url_for('spending'))
    spendings = Spending.query.filter_by(spender=current_user)
    return render_template('spending.html', title='Spending', form=form, spendings=spendings)

@app.route("/spending/update/<int:spending_id>", methods=['GET', 'POST'])
@login_required
def update_spending(spending_id):
    spending = Spending.query.get_or_404(spending_id)
    if spending.spender != current_user:
        abort(403)
    form = UpdateSpendingForm()
    if form.validate_on_submit():
        spending.description = form.description.data
        spending.amount = form.amount.data
        db.session.commit()
        flash('Your spending has been updated!', 'success')
        return redirect(url_for('spending'))
    elif request.method == 'GET':
        form.description.data = spending.description
        form.amount.data = spending.amount
    return render_template('update_spending.html', title='Update Spending', form=form)

@app.route("/spending/delete/<int:spending_id>", methods=['POST'])
@login_required
def delete_spending(spending_id):
    spending = Spending.query.get_or_404(spending_id)
    if spending.spender != current_user:
        abort(403)
    db.session.delete(spending)
    db.session.commit()
    flash('Your spending has been deleted!', 'success')
    return redirect(url_for('spending'))

@app.route('/create_link_token', methods=['POST'])
@login_required
def create_link_token():
    configuration = Configuration(
        host='https://sandbox.plaid.com',
        api_key={
            'clientId': app.config['PLAID_CLIENT_ID'],
            'secret': app.config['PLAID_SECRET'],
        }
    )
    configuration.verify_ssl = False  # Added this line

    api_client = ApiClient(configuration)
    client = plaid_api.PlaidApi(api_client)

    # Create a link_token for the given user
    request = link_token_create_request.LinkTokenCreateRequest(
        products=[products.Products('transactions')],
        client_name="Your App Name",
        country_codes=[country_code.CountryCode('US')],
        language='en',
        user=link_token_create_request_user.LinkTokenCreateRequestUser(
            client_user_id=str(current_user.id)
        )
    )

    try:
        response = client.link_token_create(request)
        return jsonify(response.to_dict())
    except ApiException as e:
        print(f"Exception when calling PlaidApi->link_token_create: {e}")
        return jsonify({'error': str(e)})



@app.route('/exchange_public_token', methods=['POST'])
@login_required
def exchange_public_token():
    public_token = request.json.get('public_token')

    configuration = Configuration(
        host='https://sandbox.plaid.com',
        api_key={
            'clientId': app.config['PLAID_CLIENT_ID'],
            'secret': app.config['PLAID_SECRET'],
        }
    )
    configuration.verify_ssl = False  # Added this line

    api_client = ApiClient(configuration)
    client = plaid_api.PlaidApi(api_client)

    request = item_public_token_exchange_request.ItemPublicTokenExchangeRequest(
        public_token=public_token
    )

    try:
        response = client.item_public_token_exchange(request)
        access_token = response['access_token']

        # Store access_token in the database for the user
        current_user.plaid_access_token = access_token
        db.session.commit()

        return jsonify({'message': 'Access token stored successfully'})
    except ApiException as e:
        print(f"Exception when calling PlaidApi->item_public_token_exchange: {e}")
        return jsonify({'error': str(e)})



@app.route('/transactions', methods=['GET'])
@login_required
def get_transactions():
    configuration = Configuration(
        host='https://sandbox.plaid.com',
        api_key={
            'clientId': app.config['PLAID_CLIENT_ID'],
            'secret': app.config['PLAID_SECRET'],
        }
    )
    configuration.verify_ssl = False  # Added this line

    api_client = ApiClient(configuration)
    client = plaid_api.PlaidApi(api_client)

    access_token = current_user.plaid_access_token
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')

    request = transactions_get_request.TransactionsGetRequest(
        access_token=access_token,
        start_date=start_date,
        end_date=end_date,
        options=transactions_get_request_options.TransactionsGetRequestOptions(count=100, offset=0)
    )

    try:
        response = client.transactions_get(request)
        transactions = response['transactions']
        return render_template('transactions.html', transactions=transactions)
    except ApiException as e:
        print(f"Exception when calling PlaidApi->transactions_get: {e}")
        return jsonify({'error': str(e)})


@app.route("/stocks")
@login_required
def stocks():
    # Initialize the Alpha Vantage API client
    ts = TimeSeries(key=app.config['ALPHA_VANTAGE_API_KEY'], output_format='json')

    # Get stock data for the S&P 500 (symbol: 'SPY')
    data, meta_data = ts.get_intraday(symbol='SPY', interval='1min', outputsize='compact')

    # Extract the time series and closing prices
    times = list(data.keys())
    closing_prices = [float(data[time]['4. close']) for time in times]

    # Reverse the order to have the most recent time on the right
    times.reverse()
    closing_prices.reverse()

    # Reduce the number of x-axis labels
    reduced_times = times[::10]  # Display every 10th label
    reduced_closing_prices = closing_prices[::10]

    # Create a Plotly graph
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=reduced_times, y=reduced_closing_prices, mode='lines', name='S&P 500'))
    fig.update_layout(
        title='S&P 500 Price',
        xaxis_title='Time',
        yaxis_title='Price',
        xaxis=dict(type='category', tickangle=-45),
        yaxis=dict(tickformat='.2f')
    )

    # Convert the plotly figure to JSON for rendering in the template
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('stocks.html', graphJSON=graphJSON)

if __name__ == '__main__':
    app.run(debug=True)
