from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

_MONGO_URL = os.environ.get("MONGO_URL", "")
_client = None
_db = None


def is_mongo_available() -> bool:
    return bool(_MONGO_URL)


def get_client():
    global _client
    if _client is None and _MONGO_URL:
        from motor.motor_asyncio import AsyncIOMotorClient
        _client = AsyncIOMotorClient(_MONGO_URL, serverSelectionTimeoutMS=3000)
    return _client


def get_db():
    global _db
    if _db is None and is_mongo_available():
        _db = get_client().rag_insights
    return _db


async def ensure_indexes():
    db = get_db()
    if db is None:
        return
    await db.queries.create_index("timestamp", expireAfterSeconds=86400 * 30)
    await db.queries.create_index("user")
    await db.queries.create_index("intent")
    await db.queries.create_index([("timestamp", -1)])
    await db.traces.create_index("query_id", unique=True)
    await db.traces.create_index("timestamp", expireAfterSeconds=86400 * 30)
    await db.traces.create_index("user")


async def log_audit_entry(entry: dict) -> None:
    db = get_db()
    if db is None:
        return
    try:
        entry["_timestamp"] = datetime.now(timezone.utc)
        await db.queries.insert_one(entry)
    except Exception as e:
        print(f"[MongoDB] log_audit_entry failed: {e}")


async def save_trace(query_id: str, trace: dict) -> None:
    db = get_db()
    if db is None:
        return
    try:
        trace["_timestamp"] = datetime.now(timezone.utc)
        await db.traces.replace_one(
            {"query_id": query_id},
            trace,
            upsert=True,
        )
    except Exception as e:
        print(f"[MongoDB] save_trace failed: {e}")


async def get_trace(query_id: str) -> dict | None:
    db = get_db()
    if db is None:
        return None
    try:
        doc = await db.traces.find_one({"query_id": query_id}, {"_id": False, "_timestamp": False})
        return doc
    except Exception as e:
        print(f"[MongoDB] get_trace failed: {e}")
        return None


async def get_analytics(
    user: str | None = None,
    intent: str | None = None,
    days: int = 7,
    limit: int = 50,
) -> dict[str, Any]:
    db = get_db()
    if db is None:
        return {"error": "MongoDB not configured"}

    match: dict[str, Any] = {}
    cutoff = datetime.now(timezone.utc)
    cutoff = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    cutoff = cutoff - timedelta(days=days)
    match["_timestamp"] = {"$gte": cutoff}
    if user:
        match["user"] = user
    if intent:
        match["intent"] = intent

    try:
        pipeline = [
            {"$match": match},
            {"$group": {
                "_id": "$intent",
                "count": {"$sum": 1},
                "avg_similarity": {"$avg": {"$ifNull": ["$similarity_score", None]}},
                "unique_users": {"$addToSet": "$user"},
            }},
            {"$sort": {"count": -1}},
        ]
        by_intent = await db.queries.aggregate(pipeline).to_list(limit)

        recent_cursor = db.queries.find(
            match,
            {"_id": False, "_timestamp": False, "answer_preview": False},
        ).sort("_timestamp", -1).limit(20)
        recent = await recent_cursor.to_list(20)

        total = await db.queries.count_documents(match)

        user_pipeline = [
            {"$match": match},
            {"$group": {
                "_id": "$user",
                "count": {"$sum": 1},
                "last_query": {"$max": "$_timestamp"},
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]
        top_users = await db.queries.aggregate(user_pipeline).to_list(10)

        return {
            "period_days": days,
            "total_queries": total,
            "by_intent": [
                {"intent": r["_id"], "count": r["count"],
                 "unique_users": len(r.get("unique_users", []))}
                for r in by_intent
            ],
            "top_users": [
                {"user": r["_id"], "queries": r["count"]}
                for r in top_users
            ],
            "recent_queries": recent,
        }
    except Exception as e:
        return {"error": str(e)}
