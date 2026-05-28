from __future__ import annotations
import os
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from models.user import User
from models.role import Role

_DATA_DIR = "data"
_USERS_PATH = os.path.join(_DATA_DIR, "users.json")
_JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-use-a-real-secret")
_JWT_ALGO = "HS256"
_JWT_TTL_HOURS = 24

# ── password helpers ────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())

# ── user store ──────────────────────────────────────────────

def _load_users() -> list[dict]:
    if not os.path.exists(_USERS_PATH):
        _seed_default_users()
    with open(_USERS_PATH, encoding="utf-8") as f:
        return json.load(f)

def _save_users(users: list[dict]) -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

def _seed_default_users() -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)
    users = [
        {
            "id": "u_admin",
            "username": "admin",
            "password_hash": hash_password("admin123"),
            "role": "admin",
            "department": "IT",
        },
        {
            "id": "u_manager",
            "username": "manager",
            "password_hash": hash_password("manager123"),
            "role": "manager",
            "department": "Engineering",
        },
        {
            "id": "u_employee",
            "username": "employee",
            "password_hash": hash_password("employee123"),
            "role": "employee",
            "department": "Engineering",
        },
        {
            "id": "u_auditor",
            "username": "auditor",
            "password_hash": hash_password("auditor123"),
            "role": "auditor",
            "department": "Compliance",
        },
    ]
    _save_users(users)
    print(f"[auth] Seeded {len(users)} default users to {_USERS_PATH}")

def authenticate(username: str, password: str) -> Optional[User]:
    users = _load_users()
    for u in users:
        if u["username"] == username and verify_password(password, u["password_hash"]):
            return User(
                id=u["id"],
                username=u["username"],
                password_hash=u["password_hash"],
                role=Role(u["role"]),
                department=u.get("department", ""),
            )
    return None

def get_user_by_id(user_id: str) -> Optional[User]:
    users = _load_users()
    for u in users:
        if u["id"] == user_id:
            return User(
                id=u["id"],
                username=u["username"],
                password_hash=u["password_hash"],
                role=Role(u["role"]),
                department=u.get("department", ""),
            )
    return None

# ── JWT helpers ─────────────────────────────────────────────

def create_token(user: User) -> str:
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role.value,
        "department": user.department,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=_JWT_TTL_HOURS),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGO)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGO])
    except jwt.PyJWTError:
        return None
