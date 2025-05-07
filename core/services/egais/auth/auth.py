from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from core.handlers.basic import get_start
from core.loggers.egais_logger import LoggerEGAIS
from core.services.egais.callbackdata import ChangeComp
from core.utils.foreman import foreman


async def change_comp(
    call: CallbackQuery,
    state: FSMContext,
    log_e: LoggerEGAIS,
    callback_data: ChangeComp,
):
    log_e.info(f"Выбрали компьютер {callback_data.shopcode}")
    cash = await foreman.get_cash(
        f"cash-{callback_data.shopcode}-{callback_data.cashcode}"
    )
    await state.update_data(foreman_cash=cash.model_dump_json(by_alias=True))
    await call.message.delete()
    await get_start(call.message, state, log_e)
