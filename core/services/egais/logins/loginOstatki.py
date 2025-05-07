from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from core.database.query_BOT import get_client_info
from core.keyboards.inline import kb_ostatki_entity, kb_ostatki
from core.loggers.egais_logger import LoggerEGAIS
from core.utils import texts
from core.utils.callbackdata import Ostatki
from core.utils.foreman.pd_model import ForemanCash
from core.utils.states import StateOstatki


async def choose_entity(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    log_e.button("Остатки")
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    await state.set_state(StateOstatki.choose_entity)
    await call.message.edit_text(
        texts.choose_entity, reply_markup=kb_ostatki_entity(cash)
    )


async def menu(
    call: CallbackQuery, state: FSMContext, callback_data: Ostatki, log_e: LoggerEGAIS
):
    client = await get_client_info(chat_id=call.message.chat.id)
    log_e.info(f'Выбрали Юр.Лицо "{callback_data.inn}"')
    await state.update_data(
        inn=callback_data.inn, fsrar=callback_data.fsrar, admin=client.admin
    )
    await state.set_state(StateOstatki.menu)
    await call.message.edit_text(
        texts.ostatki, reply_markup=kb_ostatki(callback_data.inn, callback_data.fsrar)
    )
