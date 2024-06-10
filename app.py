from flask import Flask, request, jsonify
import uuid
from firebase import db
import bcrypt
from datetime import datetime
from operate_content_model import recommend_for_user
from operate_collaborative_model import recommend_articles

app = Flask(__name__)


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
            'id': user_id,
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
                "value": int(rating),
            })
        else:
            rating_id = str(uuid.uuid1())
            db.collection("ratings").document(rating_id).set({
                "article_id": article_id,
                "user_id": user_id,
                "value": int(rating),
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
        print("recommended_articles_collab =======> ",recommended_articles)
        return jsonify(recommended_articles)
    except Exception as e:
        print(f"Error internal: {e}")
        return jsonify({"error": "Internal Server Error"}), 500




if __name__ == "__main__":
    app.run()
