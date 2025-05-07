import asyncio
import datetime
import json
import os.path
import re
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram import Bot

from config import server_path
from core.database.query_BOT import create_inventory_log
from core.keyboards.inline import kb_end_inventory, kb_detailed_inventory
from core.keyboards.reply import scanner
from core.loggers.egais_logger import LoggerEGAIS
from core.services.egais.logins.pd_models import Client
from core.utils import texts
from core.utils.anticontrafact import Anticontrafact
from core.utils.foreman.pd_model import ForemanCash
from core.utils.states import Inventory_EGAIS

anti_api = Anticontrafact()
lock = asyncio.Lock()


async def wait_busy(state: FSMContext):
    data = await state.get_data()
    if data.get("busy"):
        while True:
            await asyncio.sleep(0.5)
            data = await state.get_data()
            if not data.get("busy"):
                break
    await state.update_data(busy=True)


async def start_inventory(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    log_e.button("Начать сканирование")
    bottles = data.get("bottles")
    await state.set_state(Inventory_EGAIS.scaning)
    if bottles:
        await call.message.answer(
            texts.scanning_inventory(bottles), reply_markup=kb_end_inventory()
        )
    else:
        await call.message.answer(
            "Можете начинать сканирование. Вам достаточно в чат с ботом отсканировать акцизную марку",
            reply_markup=scanner(),
        )
    await call.answer()


async def message_inventory(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    # await wait_busy(state)
    async with lock:
        data = await state.get_data()
        bottles = data.get("bottles")
        if message.web_app_data is not None:

            def clean_and_decode(value):
                cleaned_value = value.replace("\x1d", "")
                if "\\u" in cleaned_value:
                    decoded_value = cleaned_value.encode("utf-8").decode(
                        "unicode_escape"
                    )
                else:
                    decoded_value = cleaned_value
                return decoded_value

            marks = [
                clean_and_decode(item) for item in json.loads(message.web_app_data.data)
            ]
            log_e.info(f'Отсканировал сканером марку(-и) "{marks}"')
        else:
            marks = message.text.split()
            log_e.info(f'Написали штрихкод(-а) "{marks}"')

        if bottles is None:
            bottles = []

        accept_amarks = []
        for mark in marks:
            match = 0
            if (
                re.findall("^[0-9]{8,9}$", mark)
                or re.findall("^[A-Z0-9]{150}$", mark)
                or re.findall("^[A-Z0-9]{68}$", mark)
            ):
                if bottles:
                    for amark in bottles:
                        if mark == amark or re.findall(mark, amark):
                            await message.reply(
                                texts.error_head
                                + f"Данная марка уже была отсканирована ранее"
                            )
                            match += 1
            else:
                log_e.error(f'Данная марка "{mark}"не засчитана')
                await message.reply(
                    texts.error_head
                    + f'Данная марка "{mark}" не засчитана. Она не является акцизной маркой\nПопробуйте снова отсканировать <b><u>Акцизную марку</u></b>'
                )
                match += 1

            if match == 0:
                accept_amarks.append(mark)

        if len(accept_amarks) == 0:
            await state.update_data(busy=False)
            return

        for amark in accept_amarks:
            bottles.append(amark)

        await message.answer(
            texts.scanning_inventory(bottles), reply_markup=kb_end_inventory()
        )
        await state.update_data(bottles=bottles, busy=False)


async def detailed_inventory(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    await call.message.edit_text(
        "Загрузка данных в процессе. Пожалуйста, подождите около 1 минуты."
    )
    log_e.info("Запросили детализацию инвентаризации")
    data = await state.get_data()
    bottles = await anti_api.new_bottles_tuple(data["bottles"])
    await call.message.edit_text(
        texts.detailed_inventory(bottles), reply_markup=kb_detailed_inventory()
    )


async def end_invetory(
    call: CallbackQuery, state: FSMContext, bot: Bot, log_e: LoggerEGAIS
):
    # чат айди Насти 1664855728
    await call.message.edit_text(
        "Загрузка данных в процессе. Пожалуйста, подождите около 1 минуты."
    )
    log_e.button("Завершить сканирование инвентаризации")
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    client = Client.model_validate_json(data["client"])
    count_scanned_bottles = len(data["bottles"])
    dir_path = os.path.join(server_path, "inventory", str(call.message.chat.id))
    file_name = f"{datetime.datetime.now().strftime('%d_%m_%Y__%H_%M_%S')}.txt"
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(os.path.join(dir_path, file_name), "w+") as inventory_file:
        for amark in data["bottles"]:
            inventory_file.write(f"{amark}\n")
    nastya_message = (
        f"Закончили инвентаризацию\n"
        f"Магазин: <code>{cash.shopcode}-{cash.cashcode}</code>\n"
        f"Сотовый: +{client.phone_number}\n"
        f"Отсканировано бутылок: <code>{count_scanned_bottles}</code>\n"
        f"Путь до файла: <code>\\\\192.168.2.30\\share\\server\\inventory\\{str(call.message.chat.id)}\\{file_name}</code>\n"
    )
    await bot.send_message(1664855728, nastya_message)
    await call.message.edit_text(
        "✅Инвентаризация успешна передана специалисту.\nЕсли у вас есть вопросы, можете звонить специалисту по инвентаризации +79600484366 добавочный 2"
    )
    log_e.success(
        f'Закончили инвентаризацию. Бутылок отсканировано: {count_scanned_bottles} Бутылки: {data["bottles"]}'
    )
    await create_inventory_log(
        cash_number=cash.shopcode,
        inn=cash.inn,
        user_id=call.message.chat.id,
        level="SUCCESS",
        phone=client.phone_number,
        count_bottles=count_scanned_bottles,
        file_path=f"share\\server\\inventory\\{str(call.message.chat.id)}\\{file_name}",
    )
    await state.update_data(bottles=[])
