from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from core.database.models_enum import Roles
from core.loggers.egais_logger import LoggerEGAIS
from ..keyboards.inline import kb_admins
from core.utils import texts
from core.database.query_BOT import Database

router = Router()


@router.message(Command("admin"))
async def admin(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("/admin")
    db = Database()
    client_db = await db.get_client_info(message.chat.id)
    if Roles(client_db.role.role) != Roles.ADMIN:
        log_e.error("Пользователь не админ")
        await message.answer(texts.error_head + "Вы не админ")
        return
    await message.answer(
        "Выбор тип администрирования", reply_markup=kb_admins(client_db)
    )
