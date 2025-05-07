from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from core.loggers.markirovka_logger import LoggerZnak
from core.services.edo.keyboards import inline

router = Router()


@router.callback_query(F.data == "draftbeer_menu")
async def documents_menu(call: CallbackQuery, log_m: LoggerZnak):
    log_m.button("Разливное пиво")
    await call.message.edit_text(
        "Выберите нужный тип операции", reply_markup=inline.kb_draftbeer_menu()
    )


@router.callback_query(F.data == "draftbeer_balance")
async def start_balance(call: CallbackQuery, log_e: LoggerZnak):
    log_e.button("Остатки пива")
    await call.answer("Данная кнопка в разработке")
