'''
Adding OpenAI's ChatGPT to allow
users to gain recommendations for
their personal finances.
'''
# Adding local imports
# pip install python-dotenv flask openai sqlite3
from openai import OpenAI
import os
from dotenv import load_dotenv

# Initializing OpenAI client
load_dotenv()
client = OpenAI() # by default, uses os.environ.get("OPENAI_API_KEY") 
                  # to assign api_key to the client variable

# Function to get AI's response
# Assumes user_message is a string input
def get_user_response(user_message):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        max_tokens = 150,
        temperature = 0,
        messages=[
              {"role": "system", "content": "You are a professional personal finance advisor; you are kind and helpful."},
              {"role": "user", "content": "I have $750 dollars to put into my account. How should I allocate it?"},
              {"role": "system", "content": "You should put aside some money to pay your bills and rent, and then put some in savings."},
              {"role": "user", "content": user_message}
        ]
    )
    return response.choices[0].message