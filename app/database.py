Exit code: 0
Wall time: 0.9 seconds
Output:
from __future__ import annotations

from datetime import UTC, datetime, timedelta
import re
from typing import Any
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError


class Database:
    def __init__(self, uri: str, name: str) -> None:
        self.client = AsyncIOMotorClient(uri, tz_aware=True)
        self.db: AsyncIOMotorDatabase[dict[str, Any]] = self.client[name]

    async def ensure_indexes(self) -> None:
        await self.db.files.create_index([("name_normalized", "text")])
        await self.db.files.create_index([("chat_id", 1), ("message_id", 1)], unique=True)
        await self.db.users.create_index("user_id", unique=True)
        await self.db.requests.create_index("created_at")
        await self.db.batches.create_index("batch_id", unique=True)
        await self.db.batches.create_index("expires_at", expireAfterSeconds=0)
        await self.db.daily_usage.create_index([("user_id", 1), ("day", 1)], unique=True)

    async def upsert_user(self, user_id: int, name: str, username: str | None) -> None:
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "username": username, "last_seen_at": datetime.now(UTC)},
             "$setOnInsert": {"created_at": datetime.now(UTC), "is_premium": False, "is_banned": False}},
            upsert=True,
        )

    async def save_file(self, *, chat_id: int, message_id: int, file_id: str, name: str, size: int, kind: str) -> bool:
        result = await self.db.files.update_one(
            {"chat_id": chat_id, "message_id": message_id},
            {"$setOnInsert": {"chat_id": chat_id, "message_id": message_id, "file_id": file_id,
                               "name": name, "name_normalized": name.casefold(), "size": size,
                               "kind": kind, "created_at": datetime.now(UTC)}},
            upsert=True,
        )
        return result.upserted_id is not None

    async def search_files(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        words = [word for word in re.findall(r"[\w]+", query.casefold()) if len(word) > 1]
        if not words:
            return []
        cursor = self.db.files.find({"$and": [{"name_normalized": {"$regex": re.escape(word)}} for word in words]}).sort("created_at", -1).limit(limit)
        return [document async for document in cursor]

    async def is_banned(self, user_id: int) -> bool:
        user = await self.db.users.find_one({"user_id": user_id}, {"is_banned": 1})
        return bool(user and user.get("is_banned"))

    async def set_ban(self, user_id: int, banned: bool) -> None:
        await self.db.users.update_one({"user_id": user_id}, {"$set": {"is_banned": banned}}, upsert=True)

    async def maintenance_enabled(self) -> bool:
        setting = await self.db.settings.find_one({"key": "maintenance"})
        return bool(setting and setting.get("value"))

    async def set_maintenance(self, enabled: bool) -> None:
        await self.db.settings.update_one({"key": "maintenance"}, {"$set": {"value": enabled}}, upsert=True)

    async def get_access(self, user_id: int, free_limit: int) -> tuple[bool, int, datetime | None]:
        now = datetime.now(UTC)
        user = await self.db.users.find_one({"user_id": user_id}, {"is_premium": 1, "premium_until": 1}) or {}
        expiry = user.get("premium_until")
        premium = bool(user.get("is_premium") and (expiry is None or expiry > now))
        if user.get("is_premium") and expiry is not None and expiry <= now:
            await self.db.users.update_one({"user_id": user_id}, {"$set": {"is_premium": False}})
        today = now.date().isoformat()
        usage = await self.db.daily_usage.find_one({"user_id": user_id, "day": today}, {"count": 1}) or {}
        return premium, max(0, free_limit - int(usage.get("count", 0))), expiry

    async def consume_delivery(self, user_id: int, free_limit: int) -> tuple[bool, int]:
        premium, remaining, _ = await self.get_access(user_id, free_limit)
        if premium:
            return True, -1
        if remaining <= 0:
            return False, 0
        today = datetime.now(UTC).date().isoformat()
        try:
            usage = await self.db.daily_usage.find_one_and_update(
                {"user_id": user_id, "day": today, "count": {"$lt": free_limit}},
                {"$inc": {"count": 1}, "$setOnInsert": {"user_id": user_id, "day": today}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            return False, 0
        if not usage:
            return False, 0
        return True, max(0, free_limit - int(usage["count"]))

    async def grant_premium(self, user_id: int, days: int) -> datetime:
        now = datetime.now(UTC)
        user = await self.db.users.find_one({"user_id": user_id}, {"premium_until": 1}) or {}
        current = user.get("premium_until")
        start = current if current and current > now else now
        expiry = start + timedelta(days=days)
        await self.db.users.update_one({"user_id": user_id}, {"$set": {"is_premium": True, "premium_until": expiry}}, upsert=True)
        return expiry

    async def remove_premium(self, user_id: int) -> None:
        await self.db.users.update_one({"user_id": user_id}, {"$set": {"is_premium": False}, "$unset": {"premium_until": ""}}, upsert=True)

    async def claim_referral(self, referrer_id: int, user_id: int, reward_days: int) -> bool:
        if referrer_id == user_id or not await self.db.users.find_one({"user_id": referrer_id}, {"_id": 1}):
            return False
        result = await self.db.users.update_one({"user_id": user_id, "referred_by": {"$exists": False}}, {"$set": {"referred_by": referrer_id}})
        if not result.modified_count:
            return False
        await self.grant_premium(referrer_id, reward_days)
        await self.db.users.update_one({"user_id": referrer_id}, {"$inc": {"referral_count": 1}})
        return True

    async def create_request(self, user_id: int, query: str) -> None:
        await self.db.requests.insert_one({"user_id": user_id, "query": query, "status": "open", "created_at": datetime.now(UTC)})

    async def add_to_batch(self, user_id: int, file_id: str) -> int:
        batch = await self.db.batches.find_one_and_update(
            {"user_id": user_id, "status": "building"},
            {"$setOnInsert": {"batch_id": uuid4().hex, "created_at": datetime.now(UTC), "expires_at": datetime.now(UTC) + timedelta(hours=24), "file_ids": []}, "$addToSet": {"file_ids": file_id}},
            upsert=True, return_document=ReturnDocument.AFTER,
        )
        return len(batch.get("file_ids", [])) if batch else 0

    async def finish_batch(self, user_id: int) -> dict[str, Any] | None:
        return await self.db.batches.find_one_and_update(
            {"user_id": user_id, "status": "building", "file_ids.0": {"$exists": True}}, {"$set": {"status": "ready"}}, return_document=ReturnDocument.AFTER,
        )

    async def get_batch(self, batch_id: str) -> dict[str, Any] | None:
        return await self.db.batches.find_one({"batch_id": batch_id, "status": "ready"})

    async def stats(self) -> dict[str, int]:
        return {"users": await self.db.users.count_documents({}), "files": await self.db.files.count_documents({}),
                "requests": await self.db.requests.count_documents({"status": "open"}), "premium": await self.db.users.count_documents({"is_premium": True})}

    async def close(self) -> None:
        self.client.close()

