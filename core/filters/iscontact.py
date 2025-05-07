from aiogram.filters import BaseFilter
from aiogram.types import Message

from core.loggers.make_loggers import bot_log


class IsTrueContact(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if message.contact.user_id == message.from_user.id:
            bot_log.info(f"Отправил свой сотовый '{message.contact.phone_number}'")
            return True
        else:
            bot_log.debug(f"Отправил не свой сотовый '{message.contact.phone_number}'")
            return False
