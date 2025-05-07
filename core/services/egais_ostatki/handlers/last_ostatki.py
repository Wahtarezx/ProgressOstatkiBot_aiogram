import os
from pathlib import Path

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, FSInputFile
from datetime import datetime
from core.database.query_BOT import create_ostatki_log
from core.handlers.basic import get_start
from core.loggers.egais_logger import LoggerEGAIS
from core.utils import texts
from core.utils.foreman.pd_model import ForemanCash
from core.utils.ostatki_server import get_last_file

router = Router()


async def send_ostatki(
    message: Message, file_path: Path, log_e: LoggerEGAIS, state: FSMContext
):
    if file_path.name.endswith("xlsx"):
        date = file_path.name.split(os.sep)[-1].split(".")[0]
    else:
        date = "__".join(file_path.name.split("__")[1:]).rstrip(".xml")
    date_file = datetime.strptime(date, "%Y_%m_%d__%H_%M").strftime("%d-%m-%Y %H:%M")
    await message.bot.send_document(message.chat.id, document=FSInputFile(file_path))
    log_e.success("Отправил остатки")
    await message.answer(texts.ostatki_date(date_file))
    await get_start(message, state, log_e)


@router.callback_query(F.data == "send_last_ostatki")
async def push_last_ostatki(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    try:
        log_e.button("Последние остатки")
        data = await state.get_data()
        cash = ForemanCash.model_validate_json(data["foreman_cash"])
        inn, fsrar = (data.get("ostatki_inn"), data.get("ostatki_fsrar"))
        last_file = await get_last_file(inn, fsrar, data.get("ostatki_type", "xls"))
        if not last_file:
            await call.message.edit_text(texts.error_head + "Список остатков пуст")
            return
        await call.message.delete()
        await create_ostatki_log(
            cash_number=cash.shopcode,
            user_id=call.message.chat.id,
            level="SUCCESS",
            inn=inn,
            file_path=last_file,
        )
        await send_ostatki(call.message, last_file, log_e, state)
    except FileNotFoundError:
        await call.message.answer(texts.error_head + "Список остатков пуст")
