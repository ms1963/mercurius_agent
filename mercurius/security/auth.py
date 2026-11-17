"""
Enterprise Authentication, RBAC and Session Token Management for Mercury.
Supports role hierarchy, HMAC-SHA256 session tokens, and cryptographic password hashing.
"""
from __future__ import annotations
import hashlib, hmac, time, uuid, json, base64
from typing import Dict, Optional, Any, List
from mercurius.core.types import UserRole

class AuthManager:
    def __init__(self, secret_key: str = "mercury_master_secret_2026"):
        self.secret_key = secret_key.encode("utf-8")
        self.users: Dict[str, Dict[str, Any]] = {
            "admin": {
                "user_id": "usr_admin",
                "username": "admin",
                "role": UserRole.ADMIN,
                "pwd_hash": self._hash("mercury2026"),
                "created_at": time.time()
            },
            "user": {
                "user_id": "usr_default",
                "username": "user",
                "role": UserRole.REGULAR,
                "pwd_hash": self._hash("user2026"),
                "created_at": time.time()
            }
        }
        self.api_keys: Dict[str, str] = {
            "mcy_live_admin_key_2026": "usr_admin",
            "mcy_live_user_key_2026": "usr_default"
        }
        self.revoked_tokens: set[str] = set()

    def _hash(self, pwd: str) -> str:
        return hashlib.sha256(pwd.encode("utf-8")).hexdigest()

    def register_user(self, username: str, password: str, role: UserRole = UserRole.REGULAR) -> str:
        uid = f"usr_{uuid.uuid4().hex[:8]}"
        self.users[username] = {
            "user_id": uid,
            "username": username,
            "role": role,
            "pwd_hash": self._hash(password),
            "created_at": time.time()
        }
        return uid

    def verify_credentials(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        u = self.users.get(username)
        if not u:
            return None
        if hmac.compare_digest(u["pwd_hash"], self._hash(password)):
            return {"user_id": u["user_id"], "username": u["username"], "role": u["role"]}
        return None

    def create_session_token(self, username: str, ttl_seconds: int = 86400) -> str:
        u = self.users.get(username)
        if not u:
            raise ValueError(f"User '{username}' does not exist")
        payload = {
            "user_id": u["user_id"],
            "username": u["username"],
            "role": u["role"].value if isinstance(u["role"], UserRole) else str(u["role"]),
            "exp": time.time() + ttl_seconds,
            "nonce": uuid.uuid4().hex
        }
        serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
        sig = hmac.new(self.secret_key, serialized, hashlib.sha256).hexdigest()
        token_str = f"{base64.urlsafe_b64encode(serialized).decode('utf-8')}.{sig}"
        return token_str

    def validate_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not token or token in self.revoked_tokens or "." not in token:
            return None
        try:
            body_b64, sig = token.split(".", 1)
            serialized = base64.urlsafe_b64decode(body_b64.encode("utf-8"))
            expected_sig = hmac.new(self.secret_key, serialized, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                return None
            payload = json.loads(serialized.decode("utf-8"))
            if time.time() > payload.get("exp", 0):
                return None
            return payload
        except Exception:
            return None

    def revoke_token(self, token: str):
        self.revoked_tokens.add(token)

    def authenticate_api_key(self, api_key: str) -> Optional[UserRole]:
        uid = self.api_keys.get(api_key)
        if not uid:
            return None
        for u in self.users.values():
            if u["user_id"] == uid:
                return u["role"]
        return UserRole.REGULAR
