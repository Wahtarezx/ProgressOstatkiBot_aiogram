from distutils.cmd import Command

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile

import config
from core.database.models_enum import Roles
from core.database.query_BOT import Database
from core.loggers.egais_logger import LoggerEGAIS
from core.services.provider_panel.keyboards.inline import kb_provider_start
from core.services.provider_panel.utils import create_excel_analytics
from core.utils import texts

router = Router()


@router.callback_query(F.data == "provider_analytics")
async def provider_analytics(
    call: CallbackQuery, log_e: LoggerEGAIS, state: FSMContext
):
    log_e.button("Аналитика")
    data = await state.get_data()
    await call.message.edit_text("Загрузка...\nМожет занять больше 15 минут")
    provider_inns = data.get("provider_inns")
    excel_file = await create_excel_analytics(
        provider_inns, await config.get_provider_by_inn(provider_inns[0])
    )
    await call.message.delete()
    await call.message.bot.send_document(call.message.chat.id, FSInputFile(excel_file))
