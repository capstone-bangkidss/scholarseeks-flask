import csv
from flask import Flask, request, jsonify
import uuid
from firebase import db
import bcrypt
from datetime import datetime
from load_articles import ARTICLES
from operate_content_model import recommend_for_user
from operate_collaborative_model import recommend_articles

app = Flask(__name__)


@app.get("/search")
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

@app.post("/register")
def register_user():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return "Email and password must be provided and cannot be undefined", 400

        users_ref = db.collection('users')
        query = users_ref.where('email', '==', email).stream()

        for doc in query:
            return "Email already exists!", 409

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_id = str(uuid.uuid4())
        new_user = {
            'user_id': user_id,
            'email': email,
            'password': hashed_password.decode('utf-8'),
            'createdAt':datetime.now().isoformat()
        }

        users_ref.document(user_id).set(new_user)
        return jsonify(new_user), 201

    except Exception as e:
        print(f"Error during user registration: {e}")
        return "Internal Server Error", 500
    
@app.post("/rating")
def submit_rating():
    try:
        data = request.get_json()
        rating = data.get('rating')
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
    
@app.delete("/rating")
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
    

@app.post("/content-model/get-articles")
def getArticles_content():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        if not user_id:
            return jsonify({"error": "Provide user_id!"}), 400
        recommended_articles = recommend_for_user(user_id)
        print("recommended_articles =======> ",recommended_articles)
        return jsonify(recommended_articles)
    except Exception as e:
        print(f"Error internal: {e}")
        return jsonify({"error": "Internal Server Error"}), 500
    
@app.post("/collaborative-model/get-articles")
def getArticles_collaborative():
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({"error": "Provide user_id!"}), 400
        
        recommended_articles = recommend_articles(user_id)
        return jsonify(recommended_articles)
    except Exception as e:
        print(f"Error internal: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# Function to save articles to Firebase
@app.post("/save-articles-to-db")
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
