from firebase import db
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from load_articles import ARTICLES
from load_models import MODEL_COLLABORATIVE


# Function to create article encoding
def create_articles_encoding():
    article_ids = [article['article_id'] for article in ARTICLES]
    article2article_encoded = {article_id: idx for idx, article_id in enumerate(article_ids)}
    return article2article_encoded, len(article_ids)

# Initialize article encoding
# article2article_encoded, num_articles = create_articles_encoding()

# Function to fetch and create user encoding
def fetch_and_create_users_encoding():
    users_ref = db.collection('users')
    users = {doc.id: doc.to_dict() for doc in users_ref.stream()}
    user_ids = list(users.keys())
    user2user_encoded = {user_id: idx for idx, user_id in enumerate(user_ids)}
    return user2user_encoded, users 

# # Function to recommend articles
# def recommend_articles(user_id, num_recommendations=10):
#     try:
#         user2user_encoded, users = fetch_and_create_users_encoding()
#         if user_id not in user2user_encoded:
#             return "User ID not found in the database."

#         user_encoded = user2user_encoded[user_id]

#         # Fetch ratings data for the user from Firestore
#         ratings_ref = db.collection("ratings").where("user_id", "==", user_id).stream()
#         user_ratings = [doc.to_dict() for doc in ratings_ref]

#         rated_article_ids = [rating['article_id'] for rating in user_ratings]
#         rated_article_indices = [article2article_encoded.get(article_id) for article_id in rated_article_ids if article_id in article2article_encoded]

#         # Generate article IDs for prediction
#         article_ids = np.array(list(article2article_encoded.keys()))
#         article_indices = np.array(list(article2article_encoded.values()))

#         # Filter out already rated articles
#         mask = np.isin(article_indices, rated_article_indices, invert=True)
#         article_ids = article_ids[mask]
#         article_indices = article_indices[mask]

#         # Validate indices before making predictions
#         valid_indices = article_indices < num_articles
#         article_indices = article_indices[valid_indices]
#         article_ids = article_ids[valid_indices]

#         if len(article_indices) == 0:
#             return "No articles available for recommendation."

#         # Debug statements to check the indices and input arrays
#         print(f"User encoded: {user_encoded}")
#         print(f"Article indices for prediction: {article_indices}")
#         print(f"Article indices length: {len(article_indices)}")
#         print(f"Max article index: {num_articles - 1}")
#         print(f"Total articles : {num_articles}")

        
#         user_array = np.full(len(article_ids), user_encoded)
#         prediction_input = [user_array, article_indices]

#         print(f"Prediction input: {prediction_input}")

#         ratings_pred = MODEL_COLLABORATIVE.predict(prediction_input).flatten()

#         # Sort predictions and get top recommendations
#         top_indices = ratings_pred.argsort()[-num_recommendations:][::-1]
#         top_article_ids = article_ids[top_indices]
#         top_articles = [article for article in ARTICLES if article['article_id'] in top_article_ids]

#         # Sort recommended articles by 'Cited by' in descending order
#         top_articles = sorted(top_articles, key=lambda x: x.get('Cited by', 0), reverse=True)

#         return top_articles

#     except Exception as e:
#         print(f"Error recommending articles: {e}")
#         return []

def recommend_articles(user_id, num_recommendations=12):
    try:
        df_article = pd.DataFrame(ARTICLES)
        ratings_ref = db.collection("ratings").stream()
        df_rating = pd.DataFrame([doc.to_dict() for doc in ratings_ref])
        df_rating['article_id']=df_rating['article_id'].astype(int)
        df_rating['article_rating']=df_rating['article_rating'].astype(int)
        users_ref = db.collection("users").stream()
        df_user = pd.DataFrame([{key: value for key, value in doc.to_dict().items() if key != 'rated_articles'} for doc in users_ref])

        # Merge ratings with articles and users for better context
        merged_df = pd.merge(df_rating, df_article, on='article_id')
        merged_df = pd.merge(merged_df, df_user, on='user_id')
        # print("merged_df ===>",merged_df)
        # Encode user_id and article_id
        user_ids = merged_df['user_id'].unique().tolist()
        article_ids = merged_df['article_id'].unique().tolist()

        user2user_encoded = {x: i for i, x in enumerate(user_ids)}
        article2article_encoded = {x: i for i, x in enumerate(article_ids)}


        
        
        # print("user_id ====>",user_id)
        # user2user_encoded, users = fetch_and_create_users_encoding()
        # if user_id not in user2user_encoded:
        #     return "User ID not found in the database."
        if user_id in user2user_encoded:
            # User is found in the database
            user_encoded = user2user_encoded[user_id]
            user_ratings = df_rating[df_rating['user_id'] == user_id]
            rated_article_ids = user_ratings['article_id'].tolist()
            rated_article_indices = [article2article_encoded[article_id] for article_id in rated_article_ids]
            # Generate article IDs for prediction
            article_ids = np.array(list(article2article_encoded.keys()))
            article_indices = np.array(list(article2article_encoded.values()))
            # print("user2user_encoded ====>",user2user_encoded)
            # print("article_ids ===>", article_ids)
            # print("rated_article_indices ===>", article_indices)
            # Filter out already rated articles
            mask = np.isin(article_indices, rated_article_indices, invert=True)
            article_ids = article_ids[mask]
            article_indices = article_indices[mask]
            # print("mask ===>", mask)


            user_array = np.full(len(article_ids), user_encoded)
            prediction_input = [user_array, article_indices]

            # print("prediction_input ===>", prediction_input)

            # Get model predictions
            ratings_pred = MODEL_COLLABORATIVE.predict(prediction_input).flatten()

            # Sort predictions and get top recommendations
            top_indices = ratings_pred.argsort()[-num_recommendations:][::-1]
            top_article_ids = article_ids[top_indices]
            top_articles = df_article[df_article['article_id'].isin(top_article_ids)].sort_values(by='cited_by', ascending=False)
        else:
            # User not found, recommend top-rated articles overall
            avg_ratings = df_rating.groupby('article_id')['article_rating'].mean().sort_values(ascending=False)
            top_article_ids = avg_ratings.index[:num_recommendations+1].tolist()
            top_articles = df_article[df_article['article_id'].isin(top_article_ids)].sort_values(by='cited_by', ascending=False)

        return top_articles.to_dict(orient='records')
    except Exception as e:
        print(f"Error recommending articles: {e}")
        return []