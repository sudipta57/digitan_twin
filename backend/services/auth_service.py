import os
import hashlib
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from backend.models.schemas import UserInfo

_users: dict[str, UserInfo] = {}


class AuthService:

    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")

    def verify_google_token(self, token: str) -> UserInfo:
        if not self.client_id:
            raise ValueError("GOOGLE_CLIENT_ID is not configured on the server")
        try:
            idinfo = id_token.verify_oauth2_token(
                token, google_requests.Request(), self.client_id
            )
        except Exception as e:
            raise ValueError(f"Invalid Google token: {e}")

        google_sub = idinfo["sub"]
        user_id = hashlib.sha256(google_sub.encode()).hexdigest()[:16]
        email = idinfo.get("email", "")
        name = idinfo.get("name") or (email.split("@")[0] if email else "User")

        user = UserInfo(user_id=user_id, email=email, name=name)
        _users[user_id] = user
        return user

    def get_user(self, user_id: str) -> UserInfo | None:
        return _users.get(user_id)
