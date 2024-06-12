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
def get_recommendations_legacy(article_id, cosine_sim):
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
def recommend_for_user_legacy(user_id):
    try:
        ratings = fetch_ratings()
        articles = ARTICLES

        user_article_matrix = np.zeros((len(ratings), len(articles)))
        user_index_mapping = {user_id: idx for idx, user_id in enumerate(set(r['user_id'] for r in ratings))}

        for rating in ratings:
            user_idx = user_index_mapping.get(rating['user_id'])
            article_idx = next((idx for idx, article in enumerate(articles) if article['article_id'] == rating['article_id']), None)
            if user_idx is not None and article_idx is not None:
                user_article_matrix[user_idx, article_idx] = rating['article_rating']

        user_ratings = [rating for rating in ratings if rating['user_id'] == user_id]

        if user_ratings:
            # 
            top_rated_article_id = max(user_ratings, key=lambda x: x['article_rating'])['article_id']
            similar_articles = get_recommendations_legacy(top_rated_article_id, cosine_sim)
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

def recommend_for_user(user_id, model=MODEL_CONTENT, num_recommendations=10):
    """
    Recommend articles for a given user based on their ratings and article content.

    Parameters:
    - user_id: int, the ID of the user for whom to recommend articles.
    - model: keras model, trained model for predicting user preferences.
    - num_recommendations: int, the number of articles to recommend.

    Returns:
    - DataFrame: DataFrame containing the recommended articles.
    """
    articles = pd.DataFrame(ARTICLES)
    ratings = pd.DataFrame(fetch_ratings())
    ratings['article_id']=ratings['article_id'].astype(int)
    ratings['article_rating']=ratings['article_rating'].astype(int)
    # articles_ratings = pd.merge(
    #     ratings, articles,
    #     on='article_id',
    #     how='inner',  # Ensure only matched entries are included
    #     suffixes=('_rating', '_info')  # Rename conflicting columns if any
    # )
    # print(articles_ratings)
    ratings_aggregated = ratings.groupby(['user_id', 'article_id']).agg({'article_rating': 'mean'}).reset_index()
    user_article_matrix = ratings_aggregated.pivot(index='user_id', columns='article_id', values='article_rating').fillna(0)
    # Desired shape
    num_users = 2968
    num_articles = 2494
    # Ensure the DataFrame has the correct number of users (rows)
    current_num_users = user_article_matrix.shape[0]
    if current_num_users < num_users:
        additional_users = pd.DataFrame(0.0, index=np.arange(num_users - current_num_users), columns=user_article_matrix.columns)
        user_article_matrix = pd.concat([user_article_matrix, additional_users], ignore_index=True)

    # Ensure the DataFrame has the correct number of articles (columns)
    current_num_articles = user_article_matrix.shape[1]
    if current_num_articles < num_articles:
        additional_articles = pd.DataFrame(0.0, index=user_article_matrix.index, columns=np.arange(num_articles - current_num_articles))
        user_article_matrix = pd.concat([user_article_matrix, additional_articles], axis=1)

    user_index_mapping = {user_id: idx for idx, user_id in enumerate(user_article_matrix.index)}
    if user_id in user_index_mapping:
        # Existing user logic
        user_idx = user_index_mapping[user_id]
        user_vector = user_article_matrix.iloc[user_idx].values.reshape(1, -1)  # Ensure input shape matches model expectation
        # print("articles ===>\n",articles)

        # print("user_article_matrix ===>\n",user_article_matrix)
        # print("Shape of user_article_matrix:", user_article_matrix.shape)
        # print("user_index_mapping ===>",user_index_mapping)
        # print("user_idx ===>",user_idx)
        # print("user_vector ===>",user_vector)
        predicted_ratings = model.predict(user_vector)
        recommended_articles_indices = np.argsort(predicted_ratings[0])[::-1]

        # Get articles rated by the user
        user_ratings = ratings[ratings['user_id'] == user_id]

        # Filter out articles already rated by the user
        rated_article_ids = user_ratings['article_id'].tolist()
        recommended_articles = [articles.iloc[i] for i in recommended_articles_indices if articles.iloc[i]['article_id'] not in rated_article_ids]

        # Sort similar articles by 'cited_by' in descending order
        recommended_articles = sorted(recommended_articles, key=lambda x: x['cited_by'], reverse=True)

        # Convert DataFrame to list of dictionaries
        recommended_articles_dict = pd.DataFrame(recommended_articles).head(num_recommendations).to_dict(orient='records')
        return recommended_articles_dict
    else:
        # New user logic
        input_shape = user_article_matrix.shape[1]
        user_vector = np.zeros((1, input_shape))  # Use a zero vector for new users
        predicted_ratings = model.predict(user_vector)
        recommended_articles_indices = np.argsort(predicted_ratings[0])[::-1]

        recommended_articles = articles.iloc[recommended_articles_indices[:num_recommendations]]

        # Sort recommended articles by 'cited_by' in descending order
        recommended_articles = recommended_articles.sort_values(by='cited_by', ascending=False)

        return recommended_articles.head(num_recommendations).to_dict(orient='records')
