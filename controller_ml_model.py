from flask import request, jsonify
from app import app
from middleware import token_required
from operate_content_model import recommend_for_user
from operate_collaborative_model import recommend_articles
from firebase import db

# to get 'Recommendation for you' in home page
@app.route("/content-model/get-articles",methods=["POST"])
@token_required
def getArticles_content():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        if not user_id:
            return jsonify({"error": "Provide user_id!"}), 400
        user_ref = db.collection("users").document(user_id).get()
        if not user_ref:
            return jsonify({"error": "User not found!"}), 404
        else :
            user = user_ref.to_dict()
        subject_area = user['subject_area']
        recommended_articles = recommend_for_user(user_id, subject_area)
        # print("recommended_articles =======> ",recommended_articles)
        return jsonify(recommended_articles)
    except Exception as e:
        print(f"Error internal: {e}")
        return jsonify({"error": "Internal Server Error"}), 500
    
# to get 'You may also like' in home page
@app.route("/collaborative-model/get-articles",methods=["POST"])
@token_required
def getArticles_collaborative():
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({"error": "Provide user_id!"}), 400
        
        recommended_articles = recommend_articles(user_id)
        # print("recommended_articles =======> ",len(recommended_articles))
        return jsonify(recommended_articles)
    except Exception as e:
        print(f"Error internal: {e}")
        return jsonify({"error": "Internal Server Error"}), 500
