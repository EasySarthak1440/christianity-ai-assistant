from __future__ import annotations
import os
import json
from typing import Optional

from models.user import User
from models.role import Role

_DATA_DIR = "data"
_POLICY_PATH = os.path.join(_DATA_DIR, "access_policies.json")


def _load_policies() -> dict:
    if not os.path.exists(_POLICY_PATH):
        _seed_default_policies()
    with open(_POLICY_PATH, encoding="utf-8") as f:
        return json.load(f)


def _seed_default_policies() -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)
    default = {
        "*": {
            "allowed_roles": ["*"],
            "classification": "public",
            "owner": "system",
        }
    }
    with open(_POLICY_PATH, "w", encoding="utf-8") as f:
        json.dump(default, f, indent=2)
    print(f"[policy] Seeded default access policies to {_POLICY_PATH}")


def resolve_permitted_sources(
    user: Optional[User],
    all_sources: list[str],
) -> list[str]:
    if user is None:
        return []

    policies = _load_policies()
    permitted = []

    for source in all_sources:
        policy = policies.get(source) or policies.get("*", {})
        allowed_roles = policy.get("allowed_roles", ["*"])

        if "*" in allowed_roles or user.role.value in allowed_roles:
            permitted.append(source)

    return permitted
