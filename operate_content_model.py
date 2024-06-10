from firebase import db
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from load_articles import ARTICLES
from load_models import MODEL_CONTENT


# Function to fetch index_keywords from articles collection
def fetch_index_keywords():
    try:
        index_keywords_list = []

        for article in ARTICLES:
            index_keywords = article.get('index_keywords', [])
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

# Fetch index keywords and create TF-IDF matrix and cosine similarity matrix
try:
    index_keywords = fetch_index_keywords()
    tfidf_vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf_vectorizer.fit_transform(index_keywords)
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
except Exception as e:
    print(f"Error in tfidf: {e}")


# Function to get article recommendations based on article id
def get_recommendations(article_id, cosine_sim):
    try:
        articles_df = pd.DataFrame(ARTICLES)

        if articles_df.empty:
            return "No articles found in the database."

        if 'article_id' not in articles_df.columns:
            return "The articles DataFrame does not contain 'article_id' column."

        idx = articles_df[articles_df['article_id'] == article_id].index[0]
        sim_scores = list(enumerate(cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        sim_scores = sim_scores[1:11]

        article_indices = [i[0] for i in sim_scores]
        recommended_articles = articles_df.iloc[article_indices]

        return recommended_articles.to_dict(orient='records')

    except IndexError:
        return "Article ID not found in the database."
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        return []

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

# Function to recommend articles for a user based on ratings and content
def recommend_for_user(user_id):
    try:
        ratings = fetch_ratings()
        articles = ARTICLES

        user_article_matrix = np.zeros((len(ratings), len(articles)))
        user_index_mapping = {user_id: idx for idx, user_id in enumerate(set(r['user_id'] for r in ratings))}

        for rating in ratings:
            user_idx = user_index_mapping.get(rating['user_id'])
            article_idx = next((idx for idx, article in enumerate(articles) if article['article_id'] == rating['article_id']), None)
            if user_idx is not None and article_idx is not None:
                user_article_matrix[user_idx, article_idx] = rating['value']

        user_ratings = [rating for rating in ratings if rating['user_id'] == user_id]

        if user_ratings:
            # 
            top_rated_article_id = max(user_ratings, key=lambda x: x['value'])['article_id']
            similar_articles = get_recommendations(top_rated_article_id, cosine_sim)
            similar_articles = [article for article in similar_articles if article['article_id'] not in [rating['article_id'] for rating in user_ratings]]
            similar_articles = sorted(similar_articles, key=lambda x: x.get('cited_by', 0), reverse=True)

            return similar_articles[:10]

        else:
            # untested
            predicted_ratings = MODEL_CONTENT.predict(user_article_matrix)
            recommended_article_indices = np.argsort(predicted_ratings)[::-1][:10]
            recommended_articles = [articles[i] for i in recommended_article_indices]
            recommended_articles = sorted(recommended_articles, key=lambda x: x.get('cited_by', 0), reverse=True)

            return recommended_articles

    except Exception as e:
        print(f"Error recommending articles for user {user_id}: {e}")
        return []

