from firebase import db
import pandas as pd

# Global variable to store articles
ARTICLES = []


# Function to fetch articles once FROM LOCAL CSV and store in global variable
def initialize_articles():
    global ARTICLES
    try:
        # Load articles from a local CSV file
        df_articles = pd.read_csv('articles_selected_with_doi.csv')

        # Convert the DataFrame to a list of dictionaries
        ARTICLES = df_articles.to_dict(orient='records')
    except Exception as e:
        print(f"Error fetching articles: {e}")
        ARTICLES = []

# Call this function when the app starts
initialize_articles()

# # Function to fetch articles once and store in global variable
# def initialize_articles():
#     global ARTICLES
#     try:
#         articles_ref = db.collection('articles')
#         docs = articles_ref.stream()
#         ARTICLES = [doc.to_dict() for doc in docs]
#     except Exception as e:
#         print(f"Error fetching articles: {e}")
#         ARTICLES = []

# # Call this function when the app starts
# initialize_articles()