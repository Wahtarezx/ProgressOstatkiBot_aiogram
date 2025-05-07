from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from core.database.query_BOT import get_client_info
from core.keyboards.inline import kb_entity, kb_menu_ttns, kb_whatsapp_url
from core.loggers.egais_logger import LoggerEGAIS
from core.services.egais.TTN.pd_model import Waybills
from core.utils import texts
from core.utils.UTM import UTM
from core.utils.callbackdata import ChooseEntity
from core.utils.foreman.pd_model import ForemanCash
from core.utils.states import StateTTNs


async def choose_entity(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    log_e.button("Накладные")
    await state.update_data(user_id=call.from_user.id)
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    UTM_8082 = UTM(ip=cash.ip(), port="8082").check_utm_error()
    UTM_18082 = UTM(ip=cash.ip(), port="18082").check_utm_error()
    if not UTM_18082 and not UTM_8082:
        text = (
            "Не найдено рабочих УТМов\n"
            "Возможно у вас нет интернета или выключен компьютер\n"
            "Можете написать в тех.поддержку"
        )
        msg = await texts.error_message_wp(cash, text)
        await call.message.answer(
            texts.error_head + text, reply_markup=kb_whatsapp_url(msg)
        )
        log_e.error(f"Не найдено рабочих УТМов")
        return
    await call.message.edit_text(
        texts.choose_entity, reply_markup=kb_entity(cash, UTM_8082, UTM_18082)
    )
    await state.set_state(StateTTNs.choose_entity)


async def menu(
    call: CallbackQuery,
    state: FSMContext,
    callback_data: ChooseEntity,
    log_e: LoggerEGAIS,
):
    log_e.info(f'Выбрали Юр.Лицо "{callback_data.model_dump_json()}"')
    wb = Waybills(
        inn=callback_data.inn, fsrar=callback_data.fsrar, port=callback_data.port
    )
    client = await get_client_info(call.message.chat.id)
    await state.update_data(wb=wb.model_dump_json(), admin=client.admin)
    await state.set_state(StateTTNs.menu)
    await call.message.edit_text(texts.WayBills, reply_markup=kb_menu_ttns())
