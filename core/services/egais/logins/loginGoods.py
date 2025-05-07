from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from core.keyboards.inline import kb_goods
from core.loggers.egais_logger import LoggerEGAIS
from core.utils import texts
from core.utils.foreman.pd_model import ForemanCash
from core.utils.states import Goods


async def menu_goods(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Товары")
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    await state.set_state(Goods.menu)
    await call.message.edit_text(texts.goods, reply_markup=kb_goods(cash))
