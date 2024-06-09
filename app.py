# app.py
import csv
from flask import Flask, request, jsonify
import uuid
from firebase import db
import bcrypt
from datetime import datetime
from operate_collab import recommend_articles

app = Flask(__name__)


@app.get("/")
def index():
    return "yessir"


@app.get("/tes1")
def test1():
    try:
        articles = recommend_articles("6e3e450e-ef05-4983-beff-cf68debd3b74")

        return jsonify(articles)
    except Exception as e:
        print(f"Error internal: {e}")
        return jsonify({"error": "Internal Server Error"}), 500
    

@app.post("/")
def index_post():
    return "yessir"

@app.post("/users")
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

if __name__ == "__main__":
    app.run()
