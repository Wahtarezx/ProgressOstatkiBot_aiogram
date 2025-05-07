from aiogram import F, Router
from aiogram.types import CallbackQuery, BufferedInputFile

import config
from core.loggers.markirovka_logger import LoggerZnak
from core.services.edo.callback_data import DocForInfo
from core.services.edo.keyboards import inline
from core.utils import texts
from core.utils.edo_providers.factory import EDOFactory

router = Router()


@router.callback_query(F.data == "markirovka_ttn_info")
async def docList_for_info(
    call: CallbackQuery, edo_factory: EDOFactory, log_m: LoggerZnak
):
    log_m.button("Информация о последних накладных")
    if not config.develope_mode:
        await call.message.edit_text("Загрузка накладных...")
    edoprovider = await edo_factory.get_last_edo_operator()
    docs = await edoprovider.get_documents({"limit": "70"})
    if len(docs) == 0:
        log_m.error(f"У вас нет накладных")
        await call.message.answer(
            texts.information_head + f"У вас нет не принятых накладных"
        )
        await call.answer()
        return
    await call.message.edit_text(
        "Выберите накладную", reply_markup=inline.kb_select_doc_for_info(docs)
    )


@router.callback_query(DocForInfo.filter())
async def doc_info(
    call: CallbackQuery,
    edo_factory: EDOFactory,
    callback_data: DocForInfo,
    log_m: LoggerZnak,
):
    if not config.develope_mode:
        await call.message.edit_text("Загрузка накладных...")
    log_m.info(f'Выбрали накладную для просмотра "{callback_data.id}"')
    edoprovider = await edo_factory.get_last_edo_operator()
    doc_with_pdf = await edoprovider.get_doc_info_with_pdf(callback_data.id)
    text = (
        f"<b><u>Статус</u></b>: <code>{'Принята✅' if doc_with_pdf.doc_is_acccepted else 'Ожидает действий'}</code>\n"
        f"<b><u>Документ</u></b>: <code>{doc_with_pdf.doc_name}</code>\n"
        f"<b><u>Поставщик</u></b>: <code>{doc_with_pdf.seller.name}</code>\n"
        f"<b><u>На сумму</u></b>: <code>{doc_with_pdf.total_price}</code>\n"
        f"<b><u>Тип документа</u></b>: <code>{doc_with_pdf.doc_type_name}</code>\n"
    )
    await call.message.bot.send_document(
        call.message.chat.id,
        document=BufferedInputFile(
            doc_with_pdf.pdf, filename=f"{doc_with_pdf.doc_id}.pdf"
        ),
        reply_markup=inline.kb_back_to_menu(),
        caption=text,
    )
