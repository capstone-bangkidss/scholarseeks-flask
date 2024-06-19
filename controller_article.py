import csv
from flask import Blueprint,request, jsonify
from app import app
from middleware import token_required
import uuid
from firebase import db
from load_articles import ARTICLES

# add favorite (one article)
@app.route("/articles/favorite",methods=["POST"])
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
        favorite_articles = user_data.get("favorite_articles", [])
        if article_id in favorite_articles:
            return jsonify({"message": "Article already in the favorites"}), 409
        favorite_articles.append(article_id)
        user_ref.update({
            "favorite_articles": favorite_articles,
        })

        return jsonify({"message": "Added to favorites successfully"}), 201

    except Exception as e:
        print(f"Error internal: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# delete favorite (one article)
@app.route("/articles/favorite",methods=["DELETE"])
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
            return jsonify({"message": "Removed from favorites successfully"}), 200
        else:
            return jsonify({"message": "Article not found in the favorite list"}), 404

    except Exception as e:
        print(f"Error during rating deletion: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# get all articles favorited by user_id
@app.route("/articles/favorite/<user_id>",methods=["GET"])
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
@app.route("/articles/rating",methods=["POST"])
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
        
        # check if user doc has email in it, if no, return 403
        
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
@app.route("/articles/rating",methods=["DELETE"])
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

        

        # Update the user's rated_articles array
        user_data = user_ref.to_dict()
        rated_articles = user_data.get("rated_articles", [])
        if article_id in rated_articles:
            rated_articles.remove(article_id)
            db.collection("users").document(user_id).update({
                "rated_articles": rated_articles
            })
            # Delete the rating document
            db.collection("ratings").document(rating_doc.id).delete()
            return jsonify({"message": "Rating deleted successfully"}), 200
        else:
            return jsonify({"message": "Article not found in the rating list"}), 404

    except Exception as e:
        print(f"Error during rating deletion: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# get all articles rated by user_id
@app.route("/articles/rating/<user_id>",methods=["GET"])
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
@app.route("/articles/<article_id>",methods=["GET"])
@token_required
def get_an_article(article_id):
    try:
        if not article_id:
            return "Article ID must be provided and cannot be undefined", 400
        # print(article_id)
        doc_ref = db.collection("articles").document(article_id)
        doc = doc_ref.get()
        if doc.exists:
            return jsonify(doc.to_dict()), 200
        else:
            return "Article does not exist!", 404

    except Exception as e:
        return "Internal Server Error", 500

@app.route("/search",methods=["GET"])
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



# # Function to save articles to Firebase
# @app.route("/save-articles-to-db",methods=["POST"])
# @token_required
# def save_articles_to_firebase():
#     try:
#         # Open and read the CSV file
#         with open('articles_selected_with_doi.csv', 'r', encoding='utf-8') as csv_file:
#             csv_reader = csv.DictReader(csv_file)
            
#             # Iterate over each row in the CSV file
#             for row in csv_reader:
#                 # Convert cited_by to integer
#                 row['cited_by'] = int(row['cited_by'])
                
#                 # Add empty list for rated_users
#                 row['rated_users'] = []
                
#                 # Save the article to the Firebase articles collection
#                 db.collection('articles').document(row['article_id']).set(row)
        
#         return "Articles saved to Firebase successfully."
    
#     except Exception as e:
#         return f"Error saving articles to Firebase: {e}"