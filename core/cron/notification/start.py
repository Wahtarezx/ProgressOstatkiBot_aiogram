import asyncio
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiohttp import ClientSession, ClientTimeout
from loguru import logger

import config
from core.database.modelBOT import ArtixAutologin
from core.database.models_enum import Roles
from core.database.query_BOT import Database
from core.database.query_PROGRESS import get_shipper_info
from core.keyboards.inline import kb_whatsapp_url
from core.loggers.make_loggers import exp_rutoken_log
from core.notification.query_db import (
    insert_rutoken_notifi,
    insert_ttn_notifi,
    get_all_not_send_ttn_notifi,
    get_all_not_send_rutoken_notifi,
    check_exist_rutoken,
    check_exist_ttn,
    update_to_send_ttn,
    update_to_send_rutoken,
)
from core.utils import texts
from core.utils.UTM import UTM
from core.utils.foreman.foreman import get_cash

db = Database()


async def url_ok(url: str) -> Optional[bool]:
    timeout = ClientTimeout(total=3, connect=3, sock_read=3, sock_connect=3)
    try:
        async with ClientSession() as session:
            async with session.head(url, timeout=timeout) as response:
                return response.status == 200
    except Exception as ex:
        logger.error(f"Error checking URL {url}: {ex}")
        return None


async def check_date_gost(
    ooo_name: str, date_rutoken: datetime, cash_autologin: ArtixAutologin, days: int = 7
):
    if datetime.now() > date_rutoken - timedelta(days=days):
        for c in await db.get_autologin_for_notify(
            cash_autologin.shopcode, cash_autologin.cashcode
        ):
            exp_rutoken_log.info(
                f"Вышел срок действия рутокена {ooo_name} для пользователя {c.user_id}"
            )
            client = await db.get_client_info(c.user_id)
            if not await check_exist_rutoken(
                date_rutoken, c.user_id, str(days)
            ) and Roles(client.role.role) not in [r for r in Roles if r != r.USER]:
                await insert_rutoken_notifi(
                    cash_number=f"cash-{c.shopcode}-{c.cashcode}",
                    user_id=c.user_id,
                    rutoken_date=date_rutoken,
                    days_left=days,
                    ooo_name=ooo_name,
                )


async def not_accept_ttn(utm: UTM, cash_autologin: ArtixAutologin, day_old: int = 2):
    try:
        ttns = await utm.not_accepted_ttn()
        if ttns:
            for ttn in ttns:
                if datetime.strptime(
                    ttn.ttnDate, "%Y-%m-%d"
                ) < datetime.now() - timedelta(days=365):
                    continue
                if datetime.now() > datetime.strptime(
                    ttn.ttnDate, "%Y-%m-%d"
                ) + timedelta(days=day_old):
                    for cash in await db.get_autologin_for_notify(
                        cash_autologin.shopcode, cash_autologin.cashcode
                    ):
                        client = await db.get_client_info(cash.user_id)
                        if not await check_exist_ttn(
                            str(ttn.WbRegID), str(cash.user_id)
                        ) and Roles(client.role.role) not in [
                            r for r in Roles if r != r.USER
                        ]:
                            await insert_ttn_notifi(
                                cash_number=f"cash-{cash.shopcode}-{cash.cashcode}",
                                user_id=str(cash.user_id),
                                ttn_egais=ttn.WbRegID,
                                ttn_date=ttn.ttnDate,
                                ttn_number=ttn.ttnNumber,
                                shipper_fsrar=ttn.Shipper,
                                title="У вас есть не принятая накладная",
                            )
    except Exception as e:
        logger.exception(f"Error processing TTN: {e}")


async def send_ttn_notifications(bot: Bot):
    for notifi in await get_all_not_send_ttn_notifi():
        shipper = get_shipper_info(fsrar=notifi.shipper_fsrar)
        if not shipper:
            logger.error(
                f"Не найден поставщик {notifi.shipper_fsrar} для комп {notifi.cash_number} ТТН-ЕГАИС {notifi.ttn_egais}"
            )
            continue

        text = (
            f"<b><u>{notifi.title}</u></b>\n"
            f"<b>Номер компьютера</b>: <code>{notifi.cash_number.split('-')[1]}</code>\n"
            f"<b>Поставщик</b>: <code>{shipper.name}</code>\n"
            f"<b>Номер накладной</b>: <code>{notifi.ttn_number}</code>\n"
            f"<b>Дата накладной</b>: <code>{notifi.ttn_date}</code>\n"
            f"<b>ТТН-ЕГАИС</b>: <code>{notifi.ttn_egais}</code>\n"
        )
        try:
            await update_to_send_ttn(notifi.ttn_egais, notifi.user_id)
            await bot.send_message(notifi.user_id, text)
            logger.info(
                f"Отправил уведомление ТТН {notifi.ttn_egais} пользователю {notifi.user_id}"
            )
        except TelegramForbiddenError:
            logger.error(f"Пользователь {notifi.user_id} заблокировал бота")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления ТТН: {e}")


async def send_rutoken_notifications(bot: Bot):
    for notifi in await get_all_not_send_rutoken_notifi():
        text = (
            f"{texts.intersum_head}"
            f"<b><u>У вас выходит срок действия рутокена</u></b>\n"
            f"<b>Номер компьютера</b>: <code>{notifi.cash_number.split('-')[1]}</code>\n"
            f"<b>Дата окончания</b>: <code>{notifi.rutoken_date}</code>\n"
            f"<b>Осталось дней</b>: <code>{notifi.days_left}</code>\n"
            f"<b>Юр. Лицо</b>: <code>{notifi.ooo_name}</code>\n"
        )
        try:
            await update_to_send_rutoken(notifi.rutoken_date, notifi.user_id)
            wp_msg = (
                f"Здравствуйте!\n"
                f'Это компьютер {notifi.cash_number.split("-")[1]}\n'
                f"У меня через {notifi.days_left} дней(-я) выходит срок действия рутокена\n"
                f"Проверьте пожалуйста, и перезапишите рутокен\n"
            )
            await bot.send_message(
                notifi.user_id, text, reply_markup=kb_whatsapp_url(wp_msg)
            )
            logger.info(
                f"Отправил уведомление рутокен с датой {notifi.rutoken_date}, осталось дней {notifi.days_left} пользователю {notifi.user_id}"
            )
        except TelegramForbiddenError:
            logger.error(f"Пользователь {notifi.user_id} заблокировал бота")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления рутокен: {e}")


async def create_notifications():
    used_cashes = set()
    for cash in await db.get_autologin_cashes():
        cash_key = f"cash-{cash.shopcode}-{cash.cashcode}"
        if cash_key in used_cashes:
            logger.info(f"Дубликат: {cash.shopcode}, {cash.cashcode}")
            continue

        foreman_cash = await get_cash(cash_key)
        for port in ["8082", "18082"]:
            utm = UTM(ip=foreman_cash.ip(), port=port)
            if await url_ok(utm.utm_url):
                date_rutoken = await utm.get_date_rutoken()
                if date_rutoken:
                    cash_info = await utm.get_cash_info()
                    await check_date_gost(
                        ooo_name=cash_info.get("Short_Name"),
                        date_rutoken=date_rutoken,
                        cash_autologin=cash,
                        days=3,
                    )
                await not_accept_ttn(utm, cash, day_old=1 if port == "8082" else 2)

        used_cashes.add(cash_key)


async def send_notifications():
    bot = Bot(token=config.token, parse_mode="HTML")
    await send_ttn_notifications(bot)
    await send_rutoken_notifications(bot)


if __name__ == "__main__":
    asyncio.run(create_notifications())
    asyncio.run(send_notifications())
