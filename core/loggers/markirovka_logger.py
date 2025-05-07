import json

from core.loggers.make_loggers import bot_log
from core.utils.foreman.pd_model import ForemanCash
from aiogram.types import Message


class LoggerZnak:
    def __init__(self, message: Message, st_info: dict, title: str = "[ЧЗ]"):
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
    print(
        json.dumps(
            {
                "codes": [
                    "0104670007360115215'mZ4V93XGzx",
                    "0104810268036163212q3hi49o93j3eg",
                    "0104602014011353215crs=O93Rdxp",
                    "0104607074063724215./7QQ93c1n2",
                    "0104604087001439215G1Dhf93M0ON",
                    "0104612743890259215myD5zjR4XsKq93EHm7",
                    "0104603934000250215)7tpMcC1Hh;i932Oo4",
                    "0104680036754069215BrVhPGTyGnvi93tqB5",
                ]
            }
        )
    )
