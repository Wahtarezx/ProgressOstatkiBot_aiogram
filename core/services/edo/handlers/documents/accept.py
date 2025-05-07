from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, BufferedInputFile

import config
from core.database.edo.query import EdoDB
from core.database.query_BOT import create_edoTTN_log
from core.loggers.markirovka_logger import LoggerZnak
from core.services.edo.callback_data import DocForAccept, SendAcceptDoc
from core.services.edo.keyboards import inline
from core.services.markirovka.pd_models.gismt import Participants
from core.utils import texts
from core.utils.edo_providers.factory import EDOFactory
from core.utils.foreman.pd_model import ForemanCash

router = Router()

edodb = EdoDB()


@router.callback_query(F.data == "markirovka_ttn_accept")
async def docList_for_accept(
    call: CallbackQuery, log_m: LoggerZnak, edo_factory: EDOFactory
):
    log_m.button("Подтвердить накладные")
    if not config.develope_mode:
        await call.message.edit_text("Загрузка накладных...")
    edoprovider = await edo_factory.get_last_edo_operator()
    docs = await edoprovider.get_documents_for_accept()
    if len(docs) == 0:
        log_m.error(f"У вас нет не принятых накладных")
        await call.message.answer(
            texts.information_head + f"У вас нет не принятых накладных"
        )
        await call.answer()
        return
    await call.message.edit_text(
        "Выберите накладную", reply_markup=inline.kb_select_doc_for_accept(docs)
    )


@router.callback_query(DocForAccept.filter())
async def doc_info_for_accept(
    call: CallbackQuery,
    state: FSMContext,
    callback_data: DocForAccept,
    log_m: LoggerZnak,
    edo_factory: EDOFactory,
):
    if not config.develope_mode:
        await call.message.edit_text("Загрузка накладных...")
    log_m.info(f'Выбрали накладную для приёма "{callback_data.id}"')
    edoprovider = await edo_factory.get_last_edo_operator()
    doc_with_pdf = await edoprovider.get_doc_info_with_pdf(callback_data.id)
    text = (
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
        reply_markup=inline.kb_doc_info_for_accept(doc_with_pdf.doc_id),
        caption=text,
    )


@router.callback_query(SendAcceptDoc.filter())
async def send_accept_doc(
    call: CallbackQuery,
    state: FSMContext,
    callback_data: SendAcceptDoc,
    log_m: LoggerZnak,
    edo_factory: EDOFactory,
):
    log_m.button("Принять накладную")
    if not config.develope_mode:
        await call.message.delete()
    await call.message.answer("Идёт процесс приёма...")
    data = await state.get_data()
    trueapi_profile = Participants.model_validate_json(data.get("trueapi_user_info"))
    edoprovider = await edo_factory.get_last_edo_operator()
    await edoprovider.accept_document(callback_data.id)
    doc_with_pdf = await edoprovider.get_doc_info_with_pdf(callback_data.id)
    await create_edoTTN_log(
        fio=trueapi_profile.name,
        user_id=call.message.chat.id,
        level="SUCCESS",
        operation_type="Подтвердить",
        inn=trueapi_profile.inn,
        doc_type=doc_with_pdf.doc_type_name,
        shipper_inn=doc_with_pdf.seller.inn,
        shipper_kpp=doc_with_pdf.seller.kpp,
        shipper_name=doc_with_pdf.seller.name,
        edo_provider=edo_factory.enum_edoprovider.value,
    )
    text = (
        f"{texts.success_head}"
        f"Накладная успешно принята ✅\n\n"
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
        caption=text,
    )
    log_m.success(
        f'Накладная успешно принята {doc_with_pdf.model_dump_json(exclude="pdf")}'
    )


@router.callback_query(F.data == "accept_all_EDO_docs")
async def accept_all_doc(
    call: CallbackQuery, edo_factory: EDOFactory, log_m: LoggerZnak, state: FSMContext
):
    if not config.develope_mode:
        await call.message.delete()
    log_m.button("Подтвердить все накладные")
    data = await state.get_data()
    edoprovider = await edo_factory.get_last_edo_operator()
    trueapi_profile = Participants.model_validate_json(data.get("trueapi_user_info"))
    for doc in await edoprovider.get_documents_for_accept():
        await edoprovider.accept_document(doc.doc_id)
        doc_with_pdf = await edoprovider.get_doc_info_with_pdf(doc.doc_id)
        text = (
            f"{texts.success_head}"
            f"Накладная успешно принята ✅\n\n"
            f"<b><u>Документ</u></b>: <code>{doc_with_pdf.doc_name}</code>\n"
            f"<b><u>Поставщик</u></b>: <code>{doc_with_pdf.seller.name}</code>\n"
            f"<b><u>На сумму</u></b>: <code>{doc_with_pdf.total_price}</code>\n"
            f"<b><u>Тип документа</u></b>: <code>{doc_with_pdf.doc_type_name}</code>\n"
        )
        await create_edoTTN_log(
            fio=trueapi_profile.name,
            user_id=call.message.chat.id,
            level="SUCCESS",
            operation_type="Подтвердить",
            inn=trueapi_profile.inn,
            doc_type=doc_with_pdf.doc_type_name,
            shipper_inn=doc_with_pdf.seller.inn,
            shipper_kpp=doc_with_pdf.seller.kpp,
            shipper_name=doc_with_pdf.seller.name,
            edo_provider=edo_factory.enum_edoprovider.value,
        )
        await call.message.bot.send_document(
            call.message.chat.id,
            document=BufferedInputFile(
                doc_with_pdf.pdf, filename=f"{doc_with_pdf.doc_id}.pdf"
            ),
            caption=text,
        )
    await call.message.answer("Все накладные успешно приняты✅")
