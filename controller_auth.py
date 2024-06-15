from flask import request, jsonify
from app import app
from middleware import token_required
import uuid
from firebase import db
from datetime import datetime, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests
import jwt
import os
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()


@app.route("/subject_area",methods=['POST'])
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
                'exp': datetime.now()- timedelta(hours=7)+ timedelta(hours=int(os.getenv('JWT_EXP_DELTA_HOURS')))
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

@app.route("/auth/google",methods=['POST'])
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
            'exp': datetime.now()- timedelta(hours=7)+ timedelta(hours=int(os.getenv('JWT_EXP_DELTA_HOURS')))
        }
        jwt_token = jwt.encode(payload, os.getenv('JWT_SECRET'), algorithm="HS256")
        
        # Send the JWT back to the frontend
        return jsonify({'jwt_token': jwt_token, 'user': user}), 200
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Authentication failed"}), 400
    
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