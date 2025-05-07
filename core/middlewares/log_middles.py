import json
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, ErrorEvent
from core.loggers.markirovka_logger import LoggerZnak as log_m
from core.loggers.egais_logger import LoggerEGAIS as log_e


class CallBackMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        st = data["state"]
        data["log_m"] = log_m(event.message, await st.get_data())
        data["log_e"] = log_e(event.message, await st.get_data())
        return await handler(event, data)


class MessageMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        st = data["state"]
        data["log_m"] = log_m(event, await st.get_data())
        data["log_e"] = log_e(event, await st.get_data())
        return await handler(event, data)


class ErrorEventMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[ErrorEvent, Dict[str, Any]], Awaitable[Any]],
        event: ErrorEvent,
        data: dict[str, Any],
    ) -> Any:
        st = data["state"]
        message = (
            event.update.message
            if event.update.message
            else event.update.callback_query.message
        )
        data["log_e"] = log_e(message, await st.get_data(), title="")
        return await handler(event, data)
