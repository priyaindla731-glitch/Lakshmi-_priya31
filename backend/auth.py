import jwt
import datetime
import secrets
import hashlib
import time
from functools import wraps
from flask import request, jsonify
from backend.database import get_db
import os

SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or secrets.token_urlsafe(32)

def create_token(user_id: int, role: str, email: str, full_name: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "email": email,
        "full_name": full_name,
        "jti": secrets.token_urlsafe(16),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = get_db()
    revoked = conn.execute(
        "SELECT 1 FROM revoked_tokens WHERE token_hash = ? AND expires_at > ?",
        (token_hash, int(time.time())),
    ).fetchone()
    conn.close()
    return None if revoked else payload

def revoke_token(token: str, payload: dict) -> None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = int(payload["exp"].timestamp()) if hasattr(payload["exp"], "timestamp") else int(payload["exp"])
    conn = get_db()
    conn.execute("DELETE FROM revoked_tokens WHERE expires_at <= ?", (int(time.time()),))
    conn.execute(
        "INSERT OR REPLACE INTO revoked_tokens (token_hash, expires_at) VALUES (?, ?)",
        (token_hash, expires_at),
    )
    conn.commit()
    conn.close()

def rate_limit_auth_attempt(action: str, max_attempts: int, window_seconds: int = 600) -> int:
    now = int(time.time())
    window_start = now // window_seconds * window_seconds
    client_key = request.remote_addr or "unknown"
    conn = get_db()
    conn.execute("DELETE FROM auth_rate_limits WHERE window_start < ?", (now - 86400,))
    conn.execute(
        """
        INSERT INTO auth_rate_limits (action, client_key, window_start, attempts)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(action, client_key, window_start)
        DO UPDATE SET attempts = attempts + 1
        """,
        (action, client_key, window_start),
    )
    attempts = conn.execute(
        "SELECT attempts FROM auth_rate_limits WHERE action = ? AND client_key = ? AND window_start = ?",
        (action, client_key, window_start),
    ).fetchone()["attempts"]
    conn.commit()
    conn.close()
    return max(1, window_start + window_seconds - now) if attempts > max_attempts else 0

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
            if required_role and user["role"] != required_role:
                return jsonify({"error": f"Access denied. Requires role: {required_role}"}), 403
            return f(current_user=user, *args, **kwargs)
        return decorated
    return decorator
