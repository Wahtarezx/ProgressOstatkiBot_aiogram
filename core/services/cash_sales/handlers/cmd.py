from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from ..keyboards import inline, reply
from core.loggers.egais_logger import LoggerEGAIS
from core.utils import texts

router = Router()


@router.callback_query(F.data == "cash_sales")
async def cash_sales(call: CallbackQuery, log_e: LoggerEGAIS):
    log_e.button("Продажи")
    await call.message.edit_text(
        "Выберите период продаж", reply_markup=inline.kb_select_days_sales()
    )
