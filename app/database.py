Exit code: 0
Wall time: 1 seconds
Output:
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


class Database:
    def __init__(self, uri: str, name: str) -> None:
        self.client = AsyncIOMotorClient(uri, tz_aware=True)
        self.db: AsyncIOMotorDatabase[dict[str, Any]] = self.client[name]

    async def ensure_indexes(self) -> None:
        await self.db.files.create_index([("name_normalized", "text")])
        await self.db.files.create_index([("chat_id", 1), ("message_id", 1)], unique=True)
        await self.db.users.create_index("user_id", unique=True)
        await self.db.requests.create_index("created_at")

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
        cursor = self.db.files.find({"$text": {"$search": query}}, {"score": {"$meta": "textScore"}}).sort(
            [("score", {"$meta": "textScore"})]
        ).limit(limit)
        return [document async for document in cursor]

    async def get_file(self, file_key: str) -> dict[str, Any] | None:
        return await self.db.files.find_one({"_id": file_key})

    async def create_request(self, user_id: int, query: str) -> None:
        await self.db.requests.insert_one({"user_id": user_id, "query": query, "status": "open", "created_at": datetime.now(UTC)})

    async def stats(self) -> dict[str, int]:
        return {"users": await self.db.users.count_documents({}), "files": await self.db.files.count_documents({}),
                "requests": await self.db.requests.count_documents({"status": "open"})}

    async def close(self) -> None:
        self.client.close()


