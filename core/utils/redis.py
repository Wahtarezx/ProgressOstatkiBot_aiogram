import json

import aioredis
import pickle
from typing import Optional, Any, Dict

import config


class RedisConnection:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.connection: Optional[aioredis.Redis] = None

    def check_connect(self):
        """Создание асинхронного подключения к Redis"""
        if self.connection is None:
            self.connection = aioredis.from_url(
                config.redisStorage,
            )

    async def get_data(self) -> Dict[str, Any]:
        """Метод для асинхронного получения значения по ключу из Redis"""
        self.check_connect()
        return json.loads(await self.connection.get(f"{self.user_id}"))

    async def get_cls(self, cls_name: str) -> Dict[str, Any] | None:
        """Метод для асинхронного получения класса по названию из Redis"""
        self.check_connect()
        data = await self.connection.get(f"{self.user_id}:{cls_name}")
        if data:
            return json.loads(data)

    async def set(self, **kwargs) -> None:
        """Метод для асинхронной установки значения в Redis"""
        self.check_connect()
        await self.connection.set(f"{self.user_id}", json.dumps(kwargs))

    async def set_cls(self, cls_name: str, value: Dict[str, Any]):
        """Метод для асинхронной установки значения в Redis"""
        self.check_connect()
        await self.connection.set(f"{self.user_id}:{cls_name}", json.dumps(value))

    async def close(self):
        """Метод для явного закрытия соединения"""
        if self.connection:
            await self.connection.close()
