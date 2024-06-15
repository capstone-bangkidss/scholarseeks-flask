import csv
from flask import Flask, request, jsonify
import uuid

from firebase import db
import bcrypt
from datetime import datetime, timedelta
from load_articles import ARTICLES
from operate_content_model import recommend_for_user
from operate_collaborative_model import recommend_articles
from google.oauth2 import id_token
from google.auth.transport import requests
import jwt
from functools import wraps
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration
JWT_EXP_DELTA_HOURS = 72


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'JWT token is missing!'}), 403
        try:
            token = token.split(" ")[1]  # Split "Bearer <JWT_TOKEN>"
            data = jwt.decode(token, os.getenv('JWT_SECRET'), algorithms=["HS256"])
            print(data)
            request.user = data  # Attach decoded user info to the request
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token is expired, your session has terminated!"}), 401
        except jwt.DecodeError:
            return jsonify({"error": "Failed to decode token"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)

    return decorated
        


@app.get("/search")
@token_required
def search_articles():
    try:
        query = request.args.get('query', '').lower()
        sort_by = request.args.get('sort_by', 'title').lower()
        filter_by_categories = request.args.getlist('categories')  # expecting list of categories
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))

        # Convert filter_by_categories to lowercase for case insensitive matching
        filter_by_categories = [cat.lower() for cat in filter_by_categories]

        # Search articles by title
        filtered_articles = [article for article in ARTICLES if query in article.get('title', '').lower()]

        # Filter by categories
        if filter_by_categories:
            filtered_articles = [
                article for article in filtered_articles if any(
                    cat in article.get('index_keywords', '').lower() for cat in filter_by_categories
                )
            ]

        # Sort articles
        if sort_by == 'year':
            filtered_articles.sort(key=lambda x: int(x['year']), reverse=True)
        elif sort_by == 'cited_by':
            filtered_articles.sort(key=lambda x: int(x['cited_by']), reverse=True)
        else:  # Default is to sort by title
            filtered_articles.sort(key=lambda x: x['title'].lower())

        # Pagination
        start = (page - 1) * per_page
        end = start + per_page
        paginated_articles = filtered_articles[start:end]

        return jsonify({
            'total_results': len(filtered_articles),
            'page': page,
            'per_page': per_page,
            'articles': paginated_articles
        }), 200

    except Exception as e:
        print(f"Error during search articles: {e}")
        return "Internal Server Error", 500


@app.post("/subject_area")
def submit_subject_area():
    try:
        data = request.get_json()
        subject_area = data.get('subject_area').lower()
        if not subject_area:
            return "Subject area must be provided and cannot be undefined", 400

        user_id = data.get('user_id')

        # check if session_id is authenticated
        # if unauthenticated, push new user without email and name (guest), and return it to frontend
        if not user_id:
            # create a guest account
            user_id = str(uuid.uuid4())
            new_user = {
                'user_id':user_id,
                'subject_area':subject_area,
                'email':'',
                'name':'',
                'rated_articles':[],
                'createdAt':datetime.now().isoformat()
            }
            db.collection('users').document(user_id).set(new_user)
            # Backend Issues JWT: generates a custom JWT containing user ID and other necessary claims.
            payload = {
                'user_id': user_id,
                'email': "",
                'name': "",
                'exp': datetime.now()- timedelta(hours=7)+ timedelta(hours=JWT_EXP_DELTA_HOURS)
            }
            jwt_token = jwt.encode(payload, os.getenv('JWT_SECRET'), algorithm="HS256")
            return jsonify({"jwt_token":jwt_token},{"user":new_user}), 201
        else:
            user = db.collection("users").document(user_id).get()
            if not user.exists:
                return jsonify({"error": "User not found!"}), 404
            
            db.collection('users').document(user_id).update({
                'subject_area':subject_area,
            })
            user = db.collection("users").document(user_id).get().to_dict()
            return jsonify(user), 201

    except Exception as e:
        return "Internal Server Error", 500
    
# @app.post("/register")
# @token_required
# def register_user():
#     try:
#         data = request.get_json()
#         email = data.get('email')
#         password = data.get('password')

#         if not email or not password:
#             return "Email and password must be provided and cannot be undefined", 400

#         users_ref = db.collection('users')
#         query = users_ref.where('email', '==', email).stream()

#         for doc in query:
#             return "Email already exists!", 409

#         hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
#         user_id = str(uuid.uuid4())
#         new_user = {
#             'user_id': user_id,
#             'email': email,
#             'password': hashed_password.decode('utf-8'),
#             'createdAt':datetime.now().isoformat()
#         }

#         users_ref.document(user_id).set(new_user)
#         return jsonify(new_user), 201

#     except Exception as e:
#         print(f"Error during user registration: {e}")
#         return "Internal Server Error", 500





@app.post("/auth/google")
@token_required
def auth_google():
    try:
        data = request.get_json()
        id_token_str = data.get("id_token")
        user_id = data.get("user_id")

        if not user_id:
            return "User ID must be provided and cannot be undefined", 400

        if not id_token_str:
            return "ID token must be provided and cannot be undefined", 400

        # Verify the ID token with Google
        try:
            id_info = id_token.verify_oauth2_token(id_token_str, requests.Request(), os.getenv('WEB_CLIENT_ID'))

            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')

            email = id_info.get('email')
            name = id_info.get('name', '')

        except ValueError:
            return jsonify({"error": "Invalid google token"}), 400

        # Check if the user exists in database, and create if not
        # if not authenticated, push new user without email and name (guest), and return it to frontend
        # update the guest account
        user_ref = db.collection("users").where("email", "==", email).get()
        if not user_ref:
            # update current guest to be registered account with email and name
            update_user = {
                    'email':email,
                    'name':name,
                }
            db.collection('users').document(user_id).update(update_user)
            user = db.collection("users").document(user_id).get().to_dict()
        else:
            user = db.collection("users").document(user_id).get().to_dict()
        
        # Generate a custom JWT
        payload = {
            'user_id': user_id,
            'email': email,
            'name': name,
            'exp': datetime.now()- timedelta(hours=7)+ timedelta(hours=JWT_EXP_DELTA_HOURS)
        }
        jwt_token = jwt.encode(payload, os.getenv('JWT_SECRET'), algorithm="HS256")
        
        # Send the JWT back to the frontend
        return jsonify({'jwt_token': jwt_token, 'user': user}), 200
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Authentication failed"}), 400

# add favorite (one article)
@app.post("/articles/favorite")
@token_required
def add_to_favorite():
    try:
        data = request.get_json()
        article_id = data.get('article_id')
        user_id = data.get('user_id')

        if not article_id or not user_id:
            return jsonify({"error": "Provide rating, article_id, and user_id!"}), 400
        
        # Check if the article exists
        article_ref = db.collection("articles").document(article_id).get()
        if not article_ref.exists:
            return jsonify({"error": "Article not found"}), 404
        # Check if the user exists
        user_ref = db.collection("users").document(user_id).get()
        if not user_ref.exists:
            return jsonify({"error": "User not found"}), 404
        
        # Update user's document in the "users" collection "favorite_articles" field
        user_ref = db.collection("users").document(user_id)
        user_data = user_ref.get().to_dict()
        favorites_article = user_data.get("favorite_articles", [])
        favorites_article.append(article_id)
        user_ref.update({
            "favorite_articles": favorites_article,
        })

        return jsonify({"message": "Add to favorites successfully"}), 201

    except Exception as e:
        print(f"Error internal: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# delete favorite (one article)
@app.delete("/articles/favorite")
@token_required
def remove_from_favorite():
    try:
        data = request.get_json()
        article_id = data.get('article_id')
        user_id = data.get('user_id')

        if not article_id or not user_id:
            return jsonify({"error": "Provide article_id and user_id!"}), 400

        # Check if the user exists
        user_ref = db.collection("users").document(user_id).get()
        if not user_ref.exists:
            return jsonify({"error": "User not found"}), 404

        # Update the user's favorite_articles list
        user_data = user_ref.to_dict()
        favorite_articles = user_data.get("favorite_articles", [])
        if article_id in favorite_articles:
            favorite_articles.remove(article_id)
            db.collection("users").document(user_id).update({
                "favorite_articles": favorite_articles
            })

        return jsonify({"message": "Remove from favorites successfully"}), 200

    except Exception as e:
        print(f"Error during rating deletion: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# get all articles favorited by user_id
@app.get("/articles/favorite/<user_id>")
@token_required
def get_favorite_articles(user_id):
    try:
        if not user_id:
            return "User ID must be provided and cannot be undefined", 400
        
        # Fetch user document
        doc_ref = db.collection("users").document(user_id)
        doc = doc_ref.get()
        articles_ids = []
        if doc.exists:
            articles_ids = doc.to_dict().get("favorite_articles", [])
        else:
            return "User does not exist!", 404
        
        if not articles_ids:
            return jsonify([]), 200
        
        # Fetch all articles in articles_ids
        articles_ref = db.collection("articles")
        articles = []
        for article_id in articles_ids:
            article_doc = articles_ref.document(article_id).get()
            if article_doc.exists:
                articles.append(article_doc.to_dict())
        
        return jsonify(articles), 200

    except Exception as e:
        print(f"Error fetching favorited articles: {e}")
        return "Internal Server Error", 500
    
# give rating (one article)
@app.post("/articles/rating")
@token_required
def submit_rating():
    try:
        data = request.get_json()
        rating = data.get('article_rating')
        article_id = data.get('article_id')
        user_id = data.get('user_id')

        if not rating or not article_id or not user_id:
            return jsonify({"error": "Provide rating, article_id, and user_id!"}), 400
        
        # Check if the article exists
        article_ref = db.collection("articles").document(article_id).get()
        if not article_ref.exists:
            return jsonify({"error": "Article not found"}), 404
        # Check if the user exists
        user_ref = db.collection("users").document(user_id).get()
        if not user_ref.exists:
            return jsonify({"error": "User not found"}), 404
        
        # Check if the user has already rated the article
        user_ratings_ref = db.collection("ratings").where("user_id", "==", user_id).where("article_id", "==", article_id).get()
        if user_ratings_ref:
            # If the user has already rated the article, update the existing rating
            rating_id = user_ratings_ref[0].id
            db.collection("ratings").document(rating_id).update({
                "article_rating": int(rating),
            })
        else:
            rating_id = str(uuid.uuid1())
            db.collection("ratings").document(rating_id).set({
                "article_id": article_id,
                "user_id": user_id,
                "article_rating": int(rating),
            })
            # Update or create user's document in the "users" collection
            user_ref = db.collection("users").document(user_id)
            user_data = user_ref.get().to_dict()
            rated_articles = user_data.get("rated_articles", [])
            rated_articles.append(article_id)
            user_ref.update({
                "rated_articles": rated_articles,
            })

        return jsonify({"message": "Rating submitted successfully"}), 201

    except Exception as e:
        print(f"Error internal: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# delete rating (one article)
@app.delete("/articles/rating")
@token_required
def delete_rating():
    try:
        data = request.get_json()
        article_id = data.get('article_id')
        user_id = data.get('user_id')

        if not article_id or not user_id:
            return jsonify({"error": "Provide article_id and user_id!"}), 400

        # Check if the user exists
        user_ref = db.collection("users").document(user_id).get()
        if not user_ref.exists:
            return jsonify({"error": "User not found"}), 404

        # Check if the rating exists
        ratings_ref = db.collection("ratings").where("user_id", "==", user_id).where("article_id", "==", article_id).stream()
        rating_doc = None
        for doc in ratings_ref:
            rating_doc = doc
            break
        
        if not rating_doc:
            return jsonify({"error": "Rating not found"}), 404

        # Delete the rating document
        db.collection("ratings").document(rating_doc.id).delete()

        # Update the user's rated_articles array
        user_data = user_ref.to_dict()
        rated_articles = user_data.get("rated_articles", [])
        if article_id in rated_articles:
            rated_articles.remove(article_id)
            db.collection("users").document(user_id).update({
                "rated_articles": rated_articles
            })

        return jsonify({"message": "Rating deleted successfully"}), 200

    except Exception as e:
        print(f"Error during rating deletion: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# get all articles rated by user_id
@app.get("/articles/rating/<user_id>")
@token_required
def get_rated_articles(user_id):
    try:
        if not user_id:
            return "User ID must be provided and cannot be undefined", 400
        
        # Fetch user document
        doc_ref = db.collection("users").document(user_id)
        doc = doc_ref.get()
        articles_ids = []
        if doc.exists:
            articles_ids = doc.to_dict().get("rated_articles", [])
        else:
            return "User does not exist!", 404
        
        if not articles_ids:
            return jsonify([]), 200
        
        # Fetch all articles in articles_ids
        articles_ref = db.collection("articles")
        articles = []
        for article_id in articles_ids:
            article_doc = articles_ref.document(article_id).get()
            if article_doc.exists:
                articles.append(article_doc.to_dict())
        
        return jsonify(articles), 200

    except Exception as e:
        print(f"Error fetching rated articles: {e}")
        return "Internal Server Error", 500

# get one article
@app.get("/articles/<article_id>")
@token_required
def get_an_article(article_id):
    try:
        if not article_id:
            return "Article ID must be provided and cannot be undefined", 400
        print(article_id)
        doc_ref = db.collection("articles").document(article_id)
        doc = doc_ref.get()
        if doc.exists:
            return jsonify(doc.to_dict()), 200
        else:
            return "Article does not exist!", 404

    except Exception as e:
        return "Internal Server Error", 500


    

@app.post("/content-model/get-articles")
@token_required
def getArticles_content():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        if not user_id:
            return jsonify({"error": "Provide user_id!"}), 400
        recommended_articles = recommend_for_user(user_id)
        # print("recommended_articles =======> ",recommended_articles)
        return jsonify(recommended_articles)
    except Exception as e:
        print(f"Error internal: {e}")
        return jsonify({"error": "Internal Server Error"}), 500
    
@app.post("/collaborative-model/get-articles")
@token_required
def getArticles_collaborative():
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({"error": "Provide user_id!"}), 400
        
        recommended_articles = recommend_articles(user_id)
        print("recommended_articles =======> ",len(recommended_articles))
        return jsonify(recommended_articles)
    except Exception as e:
        print(f"Error internal: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# Function to save articles to Firebase
@app.post("/save-articles-to-db")
@token_required
def save_articles_to_firebase():
    try:
        # Open and read the CSV file
        with open('articles_selected_with_doi.csv', 'r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            
            # Iterate over each row in the CSV file
            for row in csv_reader:
                # Convert cited_by to integer
                row['cited_by'] = int(row['cited_by'])
                
                # Add empty list for rated_users
                row['rated_users'] = []
                
                # Save the article to the Firebase articles collection
                db.collection('articles').document(row['article_id']).set(row)
        
        return "Articles saved to Firebase successfully."
    
    except Exception as e:
        return f"Error saving articles to Firebase: {e}"


if __name__ == "__main__":
    app.run()
