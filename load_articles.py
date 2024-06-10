from firebase import db

# Global variable to store articles
ARTICLES = []

# Function to fetch articles once and store in global variable
def initialize_articles():
    global ARTICLES
    try:
        articles_ref = db.collection('articles')
        docs = articles_ref.stream()
        ARTICLES = [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"Error fetching articles: {e}")
        ARTICLES = []

# Call this function when the app starts
initialize_articles()