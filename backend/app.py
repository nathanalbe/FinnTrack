import os
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort
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
import plotly
import plotly.graph_objs as go
import json
from forms import RegistrationForm, LoginForm, BudgetForm, SpendingForm, UpdateBudgetForm, UpdateSpendingForm, FinancialGoalForm, UpdateFinancialGoalForm

#from dotenv import load_dotenv

# Load environment variables
# load_dotenv()

app = Flask(__name__, instance_relative_config=True)
app.config['SECRET_KEY'] = '9c7f5ed4fee35fed7a039ddba384397f'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/site.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
proxied = FlaskBehindProxy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

app.config['PLAID_CLIENT_ID'] = '668d8cb09e60dd001a327cac'
app.config['PLAID_SECRET'] = 'ec04391d0ba0333547cc2a2358aab0'
app.config['PLAID_ENV'] = 'sandbox'

app.config['ALPHA_VANTAGE_API_KEY'] = os.getenv('ALPHA_VANTAGE_API_KEY')

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    plaid_access_token = db.Column(db.String(200), nullable=True)
    budgets = db.relationship('Budget', backref='owner', lazy=True)
    spendings = db.relationship('Spending', backref='spender', lazy=True)
    financial_goals = db.relationship('FinancialGoal', backref='owner', lazy=True)

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

class FinancialGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, nullable=False, default=0.0)
    due_date = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"FinancialGoal('{self.name}', '{self.target_amount}', '{self.current_amount}', '{self.due_date}')"



with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/")
@app.route("/home")
@login_required
def home():
    budgets = Budget.query.filter_by(owner=current_user).all()
    spendings = Spending.query.filter_by(spender=current_user).all()
    goals = FinancialGoal.query.filter_by(user_id=current_user.id).all()

    # Calculate total budget
    total_budget = sum(budget.amount for budget in budgets)

    # Calculate total spending
    total_spending = sum(spending.amount for spending in spendings)

    # Calculate remaining budget
    remaining_budget = total_budget - total_spending

    # Data for the pie chart
    labels = ['Spending', 'Remaining Budget']
    values = [total_spending, remaining_budget]
    colors = ['#FF5733', '#33FF57']

    # Create the pie chart
    fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, marker=dict(colors=colors))])
    fig_pie.update_layout(title='Budget vs Spending')

    # Calculate weekly data
    spendings_by_week = {}
    now = datetime.now()
    for spending in spendings:
        week_start = spending.date - timedelta(days=spending.date.weekday())
        week_start_str = week_start.strftime('%Y-%m-%d')
        if week_start_str not in spendings_by_week:
            spendings_by_week[week_start_str] = 0
        spendings_by_week[week_start_str] += spending.amount

    weekly_spendings = []
    weekly_savings = []
    weeks = []

    for i in range(len(spendings_by_week)):
        week_start_str = list(spendings_by_week.keys())[i]
        week_spending = spendings_by_week[week_start_str]
        week_saving = total_budget - week_spending
        weekly_spendings.append(week_spending)
        weekly_savings.append(week_saving)
        weeks.append(f'Week {i + 1}')

    # Create the bar chart
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(x=weeks, y=weekly_spendings, name='Weekly Spending', marker_color='blue'))
    fig_bar.add_trace(go.Bar(x=weeks, y=weekly_savings, name='Weekly Savings', marker_color='green'))

    fig_bar.update_layout(barmode='group', title='Weekly Spending and Savings')

    # Prepare data for the financial goals progress chart
    goal_names = [goal.name for goal in goals]
    current_amounts = [goal.current_amount for goal in goals]
    target_amounts = [goal.target_amount for goal in goals]

    print("Financial Goals Data")
    print("Goal Names: ", goal_names)
    print("Current Amounts: ", current_amounts)
    print("Target Amounts: ", target_amounts)

    fig_goal = go.Figure(data=[
        go.Bar(name='Current Amount', x=goal_names, y=current_amounts, marker_color='blue'),
        go.Bar(name='Target Amount', x=goal_names, y=target_amounts, marker_color='green')
    ])
    fig_goal.update_layout(barmode='group', title='Financial Goals Progress', width=700, height=400)

    graphJSON_pie = json.dumps(fig_pie, cls=plotly.utils.PlotlyJSONEncoder)
    graphJSON_bar = json.dumps(fig_bar, cls=plotly.utils.PlotlyJSONEncoder)
    graphJSON_goal = json.dumps(fig_goal, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('home.html', 
                           graphJSON_pie=graphJSON_pie, 
                           graphJSON_bar=graphJSON_bar,
                           graphJSON_goal=graphJSON_goal,
                           total_budget=total_budget, 
                           total_spending=total_spending, 
                           remaining_budget=remaining_budget)

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
    budgets = Budget.query.filter_by(owner=current_user).all()
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
    spendings = Spending.query.filter_by(spender=current_user).all()
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

@app.route("/goals", methods=['GET', 'POST'])
@login_required
def goals():
    form = FinancialGoalForm()
    if form.validate_on_submit():
        goal = FinancialGoal(
            name=form.name.data,
            target_amount=form.target_amount.data,
            current_amount=form.current_amount.data,  # Ensure current_amount is handled
            due_date=form.due_date.data,
            user_id=current_user.id
        )
        db.session.add(goal)
        db.session.commit()
        flash('Your financial goal has been created!', 'success')
        print(f"Goal added: {goal}")
        return redirect(url_for('goals'))
    else:
        print("Form validation failed")
        print(form.errors)
    goals = FinancialGoal.query.filter_by(user_id=current_user.id).all()
    print(f"Goals queried: {goals}")
    return render_template('goals.html', title='Financial Goals', form=form, goals=goals)


@app.route("/goal/update/<int:goal_id>", methods=['GET', 'POST'])
@login_required
def update_goal(goal_id):
    goal = FinancialGoal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        abort(403)
    form = UpdateFinancialGoalForm()
    if form.validate_on_submit():
        goal.name = form.name.data
        goal.target_amount = form.target_amount.data
        goal.current_amount = form.current_amount.data  # Ensure current_amount is handled
        goal.due_date = form.due_date.data
        db.session.commit()
        flash('Your goal has been updated!', 'success')
        return redirect(url_for('goals'))
    elif request.method == 'GET':
        form.name.data = goal.name
        form.target_amount.data = goal.target_amount
        form.current_amount.data = goal.current_amount
        form.due_date.data = goal.due_date
    return render_template('update_goal.html', title='Update Goal', form=form, goal=goal)

@app.route("/goal/delete/<int:goal_id>", methods=['POST'])
@login_required
def delete_goal(goal_id):
    goal = FinancialGoal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        abort(403)
    db.session.delete(goal)
    db.session.commit()
    flash('Your goal has been deleted!', 'success')
    return redirect(url_for('goals'))

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


def fetch_stock_data(symbol):
    ts = TimeSeries(key=app.config['ALPHA_VANTAGE_API_KEY'], output_format='pandas')
    data, meta_data = ts.get_daily(symbol=symbol, outputsize='compact')
    data.reset_index(inplace=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data['date'], y=data['4. close'], mode='lines', name='Close'))
    fig.update_layout(title=f'Daily Close Prices for {symbol}', xaxis_title='Date', yaxis_title='Price (USD)')
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON

@app.route("/stocks", methods=['GET', 'POST'])
def stocks():
    form = StockSearchForm()
    symbol = 'SPY'
    graphJSON = fetch_stock_data(symbol)

    if form.validate_on_submit():
        symbol = form.symbol.data
        try:
            graphJSON = fetch_stock_data(symbol)
            return render_template('stocks.html', symbol=symbol, graphJSON=graphJSON, form=form)
        except Exception as e:
            flash('Error fetching stock data. Please check the symbol and try again.', 'danger')
            return redirect(url_for('stocks'))
            
    return render_template('stocks.html', symbol=symbol, graphJSON=graphJSON, form=form)

if __name__ == '__main__':
    app.run(debug=True)
