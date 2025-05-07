from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from ..keyboards import inline, reply
from core.loggers.egais_logger import LoggerEGAIS
from core.utils import texts

router = Router()


@router.callback_query(F.data == "loyalty_system")
async def start_loyalty_system(call: CallbackQuery, log_e: LoggerEGAIS):
    log_e.button("Система лояльности")
    await call.message.edit_text(
        "Выберите тип операции:", reply_markup=inline.kb_loyalty_menu()
    )
