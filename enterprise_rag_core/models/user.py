from __future__ import annotations

from dataclasses import dataclass

from enterprise_rag_core.models.role import Role


@dataclass
class User:
    id: str
    username: str
    password_hash: str
    role: Role
    department: str = ""
    display_name: str = ""
