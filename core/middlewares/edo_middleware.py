from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from core.utils.edo_providers.factory import EDOFactory
from core.utils.redis import RedisConnection


class EDOCallBackMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        rds = RedisConnection(event.message.chat.id)
        data["redis_connection"] = rds
        data["edo_factory"] = EDOFactory(rds)
        return await handler(event, data)


class EDOMessageMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        rds = RedisConnection(event.chat.id)
        data["redis_connection"] = rds
        data["edo_factory"] = EDOFactory(rds)
        return await handler(event, data)
