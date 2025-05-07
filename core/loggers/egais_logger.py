import asyncio
import json

from aiogram.fsm.context import FSMContext

from core.loggers.make_loggers import bot_log
from aiogram.types import Message

from core.utils.foreman.pd_model import ForemanCash


class LoggerEGAIS:
    def __init__(self, message: Message, st_info: dict, title: str = "[ЕГАИС]"):
        if st_info.get("foreman_cash"):
            self.cash = ForemanCash.model_validate_json(st_info.get("foreman_cash"))
            self.log = bot_log.bind(
                shop=f"{self.cash.shopcode}-{self.cash.cashcode}",
                first_name=message.chat.first_name,
                chat_id=message.chat.id,
            )
        else:
            self.log = bot_log.bind(
                first_name=message.chat.first_name,
                chat_id=message.chat.id,
            )

        self.t = title

    def button(self, button_name: str):
        self.log.info(f'{self.t} Нажали кнопку "{button_name}"')

    def info(self, message: str):
        self.log.info(f"{self.t} {message}")

    def debug(self, message: str):
        self.log.debug(f"{self.t} {message}")

    def error(self, message: str):
        self.log.error(f"{self.t} {message}")

    def success(self, message: str):
        self.log.success(f"{self.t} {message}")

    def exception(self, message):
        self.log.exception(f"{self.t} {message}")


if __name__ == "__main__":
    print(ForemanCash.model_validate_json({}))
