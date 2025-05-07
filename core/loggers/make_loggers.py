import os
from pathlib import Path
import config
from loguru import logger

MAIN_FORMAT = "{time} | {level} | {message} | {extra}"


# Фильтер для логов
def make_filters(name):
    def filter(record):
        return record["extra"].get("filter") == name

    return filter


# region Создание директорий для логов
main_log_dir = Path(config.dir_path, "logs")
main_log_dir.mkdir(parents=True, exist_ok=True)

curl_dir = main_log_dir / "curl"
curl_dir.mkdir(exist_ok=True)

notifi_dir = main_log_dir / "notification"
notifi_dir.mkdir(exist_ok=True)
# endregion

# region Создаёт пути для лога файлов
bot_path = main_log_dir / "bot.log"
except_path = main_log_dir / "except.log"

znak_path = curl_dir / "znak.log"
foreman_path = curl_dir / "foreman.log"
egais_path = curl_dir / "egais.log"
edo_platforma_path = curl_dir / "edo_platforma.log"
cs_path = curl_dir / "cs.log"
crypto_path = curl_dir / "crypro.log"
edolite_path = curl_dir / "edolite.log"

notifi_rutoken_path = notifi_dir / "expired_rutoken.log"
notifi_tth_path = notifi_dir / "expired_ttn.log"
# endregion


# region Создание лог файлов
async def create_loggers():
    logger.add(bot_path, format=MAIN_FORMAT, filter=make_filters("bot"))
    logger.add(except_path, format=MAIN_FORMAT, filter=make_filters("except"))

    logger.add(znak_path, format=MAIN_FORMAT, filter=make_filters("znak"))
    logger.add(foreman_path, format=MAIN_FORMAT, filter=make_filters("foreman"))
    logger.add(egais_path, format=MAIN_FORMAT, filter=make_filters("egais"))
    logger.add(
        edo_platforma_path, format=MAIN_FORMAT, filter=make_filters("edo_platforma")
    )
    logger.add(cs_path, format=MAIN_FORMAT, filter=make_filters("cs"))
    logger.add(crypto_path, format=MAIN_FORMAT, filter=make_filters("crypto"))
    logger.add(edolite_path, format=MAIN_FORMAT, filter=make_filters("edolite"))

    logger.add(
        notifi_rutoken_path, format=MAIN_FORMAT, filter=make_filters("expired_rutoken")
    )
    logger.add(notifi_tth_path, format=MAIN_FORMAT, filter=make_filters("expired_ttn"))


# endregion

# region Переменные для логирования
bot_log = logger.bind(filter="bot")
except_log = logger.bind(filter="except")

znak_log = logger.bind(filter="znak")
foreman_log = logger.bind(filter="foreman")
egais_log = logger.bind(filter="egais")
edo_platforma_log = logger.bind(filter="edo_platforma")
cs_log = logger.bind(filter="cs")
crypto_log = logger.bind(filter="crypto")
edolite_log = logger.bind(filter="edolite")

exp_rutoken_log = logger.bind(filter="expired_rutoken")
exp_ttn_log = logger.bind(filter="expired_ttn")
# endregion
