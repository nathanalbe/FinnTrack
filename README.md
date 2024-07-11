# FinTrack README

## Overview

FinTrack is a personal finance management application designed to help users keep track of their budgets, expenses, and investments. This application integrates with financial data APIs to provide real-time updates and insights. 

### Features

1. **Home**
    - Displays a default stock market graph (S&P 500).
    - Overview of the user's budget for the current month.

2. **Stocks**
    - Displays the user's investments.
    - Allows users to view different stock markets.
    - Provides recommendations based on news and chart data.

3. **Budget**
    - Allows users to create and modify their monthly budget.
    - Inputs for cost of living expenses (rent, food, bills) and incoming payments.

### Tech Stack

**Backend:**
- Flask
- SQLite

**Frontend:**
- HTML/CSS
- ReactJS
- VueJS
- AngularJS

**APIs and Libraries:**
- **Plaid:** For financial data aggregation and transactions. [Plaid Documentation](https://plaid.com/docs/)
- **Alpha Vantage:** For stock market data. [Alpha Vantage Documentation](https://www.alphavantage.co/documentation/)
- **OpenAI:** For suggestions and insights. [OpenAI Documentation](https://platform.openai.com/docs/overview)

**Frontend Tools:**
- **Font Awesome:** For free web icons. [Font Awesome](https://fontawesome.com/)
- **OpenAI Chatbot Widget:** For integrating a chatbot assistant into the frontend. [OpenWidget Chat Interface](https://openwidget.com/widgets/chat-interface-for-open-ai-assistants)

### Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/FinTrack.git
    cd FinTrack
    ```

2. Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4. Set up environment variables:
    - Create a `.env` file in the root directory and add your configuration:
        ```bash
        SECRET_KEY='your_secret_key'
        SQLALCHEMY_DATABASE_URI='sqlite:///../instance/site.db'
        PLAID_CLIENT_ID='your_plaid_client_id'
        PLAID_SECRET='your_plaid_secret'
        PLAID_ENV='sandbox'
        ALPHA_VANTAGE_API_KEY='your_alpha_vantage_api_key'
        OPENAI_API_KEY='your_openai_api_key'
        ```

5. Initialize the database:
    ```bash
    flask db upgrade
    ```

6. Run the application:
    ```bash
    flask run
    ```

### Usage

- **Home Page:** Displays the S&P 500 stock market graph and an overview of the user's monthly budget.
- **Register/Login:** Users can register and log in to their accounts.
- **Budget Management:** Users can create, update, and delete budget items.
- **Spending Management:** Users can add, update, and delete spending entries.
- **Stock Market:** Users can view the stock market graph and their investments.
- **Chat**: Users can ask financial queries to the AI chatbot.

### Contributing

1. Fork the repository.
2. Create a new branch:
    ```bash
    git checkout -b feature/your-feature-name
    ```
3. Make your changes and commit them:
    ```bash
    git commit -m "Add your commit message"
    ```
4. Push to the branch:
    ```bash
    git push origin feature/your-feature-name
    ```
5. Open a pull request.

### License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.


---

