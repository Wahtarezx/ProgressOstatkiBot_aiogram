import asyncio

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import Message, CallbackQuery

from core.loggers.egais_logger import LoggerEGAIS


async def check_tg_channel_sub(bot: Bot, user_id: int) -> bool:
    user_channel_status = await bot.get_chat_member(
        chat_id="@egais116", user_id=user_id
    )

    if user_channel_status.status != ChatMemberStatus.LEFT:
        return True
    return False


async def wait_to_subscribe(
    call: CallbackQuery, wait_seconds: int = 180
) -> bool | None:
    count = 0
    while count < wait_seconds:
        check_sub = await check_tg_channel_sub(call.message.bot, call.from_user.id)
        if not check_sub:
            await asyncio.sleep(1)
            count += 1
        else:
            return True
