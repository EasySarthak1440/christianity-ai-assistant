from __future__ import annotations
from dataclasses import dataclass, field
from models.role import Role


@dataclass
class User:
    id: str
    username: str
    password_hash: str
    role: Role
    department: str = ""
    display_name: str = ""
