from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from core.handlers.basic import get_start
from core.keyboards.inline import kb_startMenu
from core.utils.foreman.pd_model import ForemanCash
from ..keyboards import inline, reply
from core.loggers.egais_logger import LoggerEGAIS
from core.utils import texts

router = Router()


@router.callback_query(F.data == "profile")
async def cb_profile(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Информация о кассе")
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    full_text, error_messages = await texts.profile(cash=cash)
    await call.message.edit_text(text=full_text, reply_markup=inline.kb_profile())


@router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Выход из профиля в главное меню")
    await get_start(call.message, state, log_e)
    await call.message.delete()
