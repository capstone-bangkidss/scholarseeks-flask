from flask import request, jsonify
from app import app
from middleware import token_required
from operate_content_model import recommend_for_user
from operate_collaborative_model import recommend_articles

@app.route("/content-model/get-articles",methods=["POST"])
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
    
@app.route("/collaborative-model/get-articles",methods=["POST"])
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
