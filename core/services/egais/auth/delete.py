from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.formatting import as_marked_section, as_list

from core.database import query_BOT
from core.database.query_BOT import del_artix_autologin, del_artix_autologins
from core.keyboards import inline
from core.loggers.egais_logger import LoggerEGAIS
from core.services.egais.callbackdata import DelComp


async def start_delete(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Удалить компьютер")
    client_db = await query_BOT.get_client_info(chat_id=call.message.chat.id)
    await call.message.edit_text(
        "Выберите номер компьютера который хотите <u><b>удалить</b></u>",
        reply_markup=inline.kb_delComp(client_db),
    )


async def delete_all_save_comp(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Удалить все компьютеры")
    client_db = await query_BOT.get_client_info(chat_id=call.message.chat.id)
    to_delete_msg = as_marked_section("Удалены следующие сохранённые компы",
                                      *[f"{comp.shopcode}-{comp.cashcode}" for comp in client_db.autologins],
                                      marker='❌')
    await del_artix_autologins([comp.id for comp in client_db.autologins])
    await call.message.edit_text(**to_delete_msg.as_kwargs())


async def end_delete(
        call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS, callback_data: DelComp
):
    log_e.info(f"Выбрали компьютер {callback_data.shopcode}")
    await del_artix_autologin(callback_data.id)
    client_db = await query_BOT.get_client_info(chat_id=call.message.chat.id)
    await call.message.delete()
    await call.message.answer(
        f"✅Вы успешно удалили компьютер {callback_data.shopcode}"
    )
    await call.message.answer(
        "Выберите нужный номер компьютера", reply_markup=inline.kb_changeComp(client_db)
    )
