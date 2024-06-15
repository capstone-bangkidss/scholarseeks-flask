from flask import request, jsonify
import jwt
import os
from dotenv import load_dotenv
from functools import wraps
# Load environment variables from .env file
load_dotenv()

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