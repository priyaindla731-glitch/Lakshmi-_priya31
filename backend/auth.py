import jwt
import datetime
import secrets
from functools import wraps
from flask import request, jsonify
from backend.database import get_db, hash_password
import os

SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or secrets.token_urlsafe(32)

def create_token(user_id: int, role: str, email: str, full_name: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "email": email,
        "full_name": full_name,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_current_user():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        return None
    
    conn = get_db()
    user = conn.execute("SELECT id, email, phone, full_name, role, preferred_language, high_contrast, speech_speed FROM users WHERE id = ?", (payload["user_id"],)).fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

def require_auth(required_role=None):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Authentication token is missing or invalid. Please log in."}), 401
            if required_role and user["role"] != required_role and user["role"] != "admin":
                return jsonify({"error": f"Access denied. Requires role: {required_role}"}), 403
            return f(current_user=user, *args, **kwargs)
        return decorated
    return decorator
