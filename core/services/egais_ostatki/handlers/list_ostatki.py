import os
from pathlib import Path

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

import config
from core.database.query_BOT import create_ostatki_log
from core.loggers.egais_logger import LoggerEGAIS
from core.services.egais_ostatki.callback_data import OstatkiChooseList
from core.services.egais_ostatki.handlers.last_ostatki import send_ostatki
from core.services.egais_ostatki.keyboards.inline import kb_choose_list_ostatki
from core.utils import texts
from core.utils.foreman.pd_model import ForemanCash
from core.utils.ostatki_server import get_last_files

router = Router()


@router.callback_query(F.data == "select_list_ostatki")
async def choose_list_ostatki(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    log_e.button("Список по датам")
    data = await state.get_data()
    inn, fsrar = (data.get("ostatki_inn"), data.get("ostatki_fsrar"))
    list_files = await get_last_files(inn, fsrar, data.get("ostatki_type", "xls"))
    if not list_files:
        await call.message.edit_text(texts.error_head + "Список остатков пуст")
        return
    await call.message.edit_text(
        texts.list_ostatki, reply_markup=kb_choose_list_ostatki(list_files)
    )


@router.callback_query(OstatkiChooseList.filter())
async def push_list_ostatki(
    call: CallbackQuery,
    callback_data: OstatkiChooseList,
    state: FSMContext,
    log_e: LoggerEGAIS,
):
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    inn, fsrar = (data.get("ostatki_inn"), data.get("ostatki_fsrar"))
    file_path = Path(
        config.server_path,
        "ostatki",
        inn,
        fsrar,
        data.get("ostatki_type", "xls"),
        callback_data.file_name,
    )
    await call.message.delete()
    await create_ostatki_log(
        cash_number=cash.shopcode,
        user_id=call.message.chat.id,
        level="SUCCESS",
        inn=inn,
        file_path=file_path,
    )
    await send_ostatki(call.message, file_path, log_e, state)
