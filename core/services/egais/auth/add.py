from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from core.loggers.egais_logger import LoggerEGAIS
from core.utils import texts
from core.utils.states import Auth


async def start_add_comp(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Добавить компьютер")
    await call.message.edit_text(
        texts.auth_head + "Напишите ответным сообщением номер вашего компьютера"
    )
    await state.set_state(Auth.send_cash_number)
