from firebase import db
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import tensorflow as tf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
# Variables to hold the models
model_content = None
model_collaborative = None

def load_models():
    global model_content, model_collaborative
    
    # Path to the .keras model file (adjust the path as needed)
    content_model_path = 'ContentBasedFilteringModel.keras'

    # collaborative_model_path = 'CollaborativeFilteringModel.keras'

    
    try:
        # Load the .keras model directly
        content_model = tf.keras.models.load_model(content_model_path)
        # collaborative_model = tf.keras.models.load_model(collaborative_model_path)

        
        # Assign the loaded model to the global variable
        model_content = content_model
        # model_collaborative = collaborative_model
        
        print("Content model loaded successfully")
    
    except Exception as e:
        print(f"Error loading content model: {e}")

try:
    load_models()
except Exception as e:
    print(f"Error loading models: {e}")



# Fetch users, ratings, and articles data from Firebase
def fetch_data():
    try:
        users_ref = db.collection('users')
        ratings_ref = db.collection('ratings')
        articles_ref = db.collection('articles')

        users = {doc.id: doc.to_dict() for doc in users_ref.stream()}
        ratings = [doc.to_dict() for doc in ratings_ref.stream()]
        articles = {doc.id: doc.to_dict() for doc in articles_ref.stream()}
        return users, ratings, articles

    except Exception as e:
        return e
try:
    load_models()
except Exception as e:
    print(f"Error loading models: {e}")



# Function to fetch index_keywords from articles collection
def fetch_index_keywords():
    try:
        articles_ref = db.collection('articles')
        index_keywords_list = []

        # Fetch all documents in the collection
        docs = articles_ref.stream()

        # Extract index_keywords from each document
        for doc in docs:
            index_keywords = doc.to_dict().get('index_keywords', [])
            if isinstance(index_keywords, list):
                # Flatten nested lists and convert non-string elements to strings
                index_keywords_list.extend([str(keyword) for sublist in index_keywords for keyword in sublist])
            elif isinstance(index_keywords, str):
                # If index_keywords is already a string, append it directly
                index_keywords_list.append(index_keywords)

        return index_keywords_list

    except Exception as e:
        print(f"Error fetching index_keywords: {e}")
        return []

try:
    # Example usage
    index_keywords = fetch_index_keywords()
    # Step 2: Create TF-IDF matrix based on index keywords from articles
    tfidf_vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf_vectorizer.fit_transform(index_keywords)

    # Step 3: Compute Cosine Similarity matrix
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
except Exception as e:
    print(f"Error fi tfidf: {e}")


# # Function to get article recommendations based on article id
# def get_recommendations(article_id, cosine_sim):
#     try:
#         articles_ref = db.collection('articles')

#         # Fetch all documents in the collection
#         docs = articles_ref.stream()

#         # Initialize variables
#         idx = None
#         articles = {}

#         # Iterate over documents to find the index of the requested article
#         for doc in docs:
#             data = doc.to_dict()
#             if data.get('article_id') == article_id:
#                 idx = len(articles) - 1
#             articles[data.get('article_id')] = data
        
#         print("idx===>",idx)

#         # If the article ID is found, proceed with recommendations
#         if idx is not None:
#             sim_scores = list(enumerate(cosine_sim[idx]))
#             sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
#             sim_scores = sim_scores[1:11]  # Get top 10 similar articles
#             article_indices = [i[0] for i in sim_scores]

#             # Retrieve similar articles from the articles dictionary
#             recommended_articles = [articles.get(article_id) for article_id in articles.keys() if article_id in article_indices]

#             return recommended_articles

#         else:
#             print("Article ID not found in the database.")
#             return "Article ID not found in the database."

#     except Exception as e:
#         print(f"Error getting recommendations: {e}")
#         return []

# Function to get article recommendations based on article id
def get_recommendations(article_id, cosine_sim):
    idx = article_id
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:11]  # Get top 10 similar articles
    
    articles_ref = db.collection('articles')

    # Fetch all documents in the collection
    docs = articles_ref.stream()

    # Initialize variables
    idx = None
    articles = {}

    # Iterate over documents to find the index of the requested article
    for doc in docs:
        data = doc.to_dict()
        articles[data.get('article_id')] = data
    if idx is not None:
        sim_scores = list(enumerate(cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        sim_scores = sim_scores[1:11]  # Get top 10 similar articles
        article_indices = [i[0] for i in sim_scores]
        # Retrieve similar articles from the articles dictionary
        recommended_articles = [articles.get(article_id) for article_id in articles.keys() if article_id in article_indices]
        return recommended_articles
    else:
        print("Article ID not found in the database.")
        return "Article ID not found in the database."

# Function to get user ratings from Firestore
def fetch_ratings():
    try:
        ratings_ref = db.collection('ratings')
        docs = ratings_ref.stream()
        ratings = []

        for doc in docs:
            data = doc.to_dict()
            ratings.append(data)

        return ratings

    except Exception as e:
        print(f"Error fetching ratings: {e}")
        return []

# Function to get article data from Firestore
def fetch_articles():
    try:
        articles_ref = db.collection('articles')
        docs = articles_ref.stream()
        articles = []

        for doc in docs:
            data = doc.to_dict()
            articles.append(data)

        return articles

    except Exception as e:
        print(f"Error fetching articles: {e}")
        return []

# Function to recommend articles for a user based on ratings and content
def recommend_for_user(user_id):
    try:
        ratings = fetch_ratings()
        articles = fetch_articles()

        # Create user-article rating matrix
        user_article_matrix = np.zeros((len(ratings), len(articles)))

        # Map user_id to the index in the user_article_matrix
        user_index_mapping = {user_id: idx for idx, user_id in enumerate(set(r['user_id'] for r in ratings))}

        # Fill user-article matrix with ratings
        for rating in ratings:
            user_idx = user_index_mapping.get(rating['user_id'])
            article_idx = next((idx for idx, article in enumerate(articles) if article['article_id'] == rating['article_id']), None)
            if user_idx is not None and article_idx is not None:
                user_article_matrix[user_idx, article_idx] = rating['value']

        # Fetch articles rated by the user
        user_ratings = [rating for rating in ratings if rating['user_id'] == user_id]

        if user_ratings:

            # Find the highest rated article by the user
            top_rated_article_id = max(user_ratings, key=lambda x: x['value'])['article_id']
            print("top_rated_article_id",top_rated_article_id)
            print("cosine_sim",cosine_sim)
            # Get recommendations based on the highest rated article
            similar_articles = get_recommendations(top_rated_article_id,cosine_sim)
            print("similar_articles",similar_articles)
            # Filter out articles already rated by the user
            similar_articles = [article for article in similar_articles if article['article_id'] not in [rating['article_id'] for rating in user_ratings]]

            # Sort similar articles by cited_by in descending order
            similar_articles = sorted(similar_articles, key=lambda x: x.get('cited_by', 0), reverse=True)

            return similar_articles[:10]

        else:
            # Recommend based on predicted ratings if user has no ratings
            predicted_ratings = model_content.predict(user_article_matrix)
            recommended_article_indices = np.argsort(predicted_ratings)[::-1][:10]
            recommended_articles = [articles[i] for i in recommended_article_indices]

            # Sort recommended articles by cited_by in descending order
            recommended_articles = sorted(recommended_articles, key=lambda x: x.get('cited_by', 0), reverse=True)

            return recommended_articles

    except Exception as e:
        print(f"Error recommending articles for user {user_id}: {e}")
        return []

# Example: Get recommendations for a user with user_id 
recommended_articles = recommend_for_user("6e3e450e-ef05-4983-beff-cf68debd3b74")
print("recommended_articles =======> ",recommended_articles)



def recommend_articles(user_id, num_recommendations=10):
    try:
        users, ratings, articles = fetch_data()
        user2user_encoded = {uid: idx for idx, uid in enumerate(users.keys())}
        article2article_encoded = {aid: idx for idx, aid in enumerate(articles.keys())}
        article2article_decoded = {idx: aid for aid, idx in article2article_encoded.items()}

        if user_id in users:
            user_encoded = user2user_encoded[user_id]
            user_ratings = [r for r in ratings if r['user_id'] == user_id]
            rated_article_ids = [r['article_id'] for r in user_ratings]
            rated_article_indices = [article2article_encoded[article_id] for article_id in rated_article_ids]
            
            # Prepare user_array containing user_encoded
            user_array = np.full(len(rated_article_indices), user_encoded)

            # Convert rated_article_indices to numpy array
            article_indices = np.array(rated_article_indices)

            # Ensure rated articles are not empty before creating prediction_input
            if len(article_indices) > 0:
                prediction_input = [user_array, article_indices]

                # Adjust input to match model's input requirements
                prediction_input = [np.expand_dims(arr, axis=0) for arr in prediction_input]

                ratings_pred = model_collaborative.predict(prediction_input).flatten()

                top_indices = ratings_pred.argsort()[-num_recommendations:][::-1]
                top_article_ids = [article2article_decoded[idx] for idx in top_indices]
                top_articles = [articles[aid] for aid in top_article_ids]
                top_articles = sorted(top_articles, key=lambda x: x.get('Cited by', 0), reverse=True)

                return top_articles

            else:
                return "User has not rated any articles."

        else:
            return "User ID not found in the database."

    except Exception as e:
        return e

