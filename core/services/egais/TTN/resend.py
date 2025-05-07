import asyncio
import re

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from core.database.query_BOT import create_ttn_log
from core.database.query_PROGRESS import get_shipper_info
from core.keyboards.inline import kb_menu_resend_ttns, kb_whatsapp_url
from core.loggers.egais_logger import LoggerEGAIS
from core.services.egais.TTN.pd_model import Waybills
from core.utils import texts
from core.utils.UTM import UTM
from core.utils.callbackdata import ResendTTN
from core.utils.foreman.pd_model import ForemanCash
from core.utils.states import ResendTTNfromText


async def resend_start_menu(call: CallbackQuery, log_e: LoggerEGAIS):
    log_e.button("Перевыслать ТТН")
    await call.message.edit_text(texts.resend_ttn, reply_markup=kb_menu_resend_ttns())


async def check_recent_tickets(utm):
    tickets = await utm.get_all_opt_URLS_text_by_docType("Ticket", 10)
    # Если среди недавних тикетов была неудачная попытка перевыслать ТТН
    for ticket in tickets:
        ticket_result = utm.parse_ticket_result(ticket)
        if ticket_result.doctype == "QueryResendDoc":
            return False
    return True


async def resend_all_ttns(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    await call.message.edit_text(texts.load_information)
    log_e.info("Все не принятые ТТН")
    data = await state.get_data()
    wb = Waybills.model_validate_json(data.get("wb"))
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    utm = UTM(ip=cash.ip(), port=wb.port)
    if not await check_recent_tickets(utm):
        log_e.error(
            "Попытка перевыслать накладную была предпринята в последние 10 минут"
        )
        text = (
            "Попытка перевыслать накладную была предпринята в последние 10 минут.\n"
            "Повторная попытка будет доступна через 10 минут."
        )
        msg = await texts.error_message_wp(cash, text)
        await call.message.answer(
            texts.error_head + text, reply_markup=kb_whatsapp_url(msg)
        )
        return
    RN_ttns = await utm.get_ttns_from_ReplyNATTN()
    accepted_ttns = await utm.get_accepted_ttn()
    log_e.info(f'Найдено накладных "{len(RN_ttns)}"')
    await call.message.answer(f"Найдено накладных: <b><u>{len(RN_ttns)}</u></b>")
    WB_ttns = await utm.get_Waybill_and_FORM2REGINFO()
    for count, RN_ttn in enumerate(RN_ttns, 1):
        # Если есть накладная, то пишет что она есть
        count_ttn_in_utm = 0
        for ttn_in_utm in WB_ttns:
            if ttn_in_utm.ttn_egais == RN_ttn.WbRegID:
                count_ttn_in_utm += 1

        if count_ttn_in_utm > 0:
            shipper_info = get_shipper_info(RN_ttn.Shipper)
            text = "<b>Данная накладная уже загружена на кассу</b>\n"
            if shipper_info is None:
                text += f"Поставщик: <code>{RN_ttn.Shipper}</code>\n"
            else:
                text += f"Поставщик: <code>{shipper_info.name}</code>\n"
            text += (
                f"Дата: <code>{RN_ttn.ttnDate}</code>\n"
                f"ТТН-ЕГАИС: <code>{RN_ttn.WbRegID}</code>\n"
            )
            await call.message.answer(text)
            log_e.debug(f'Данная накладная уже загружена на кассу "{RN_ttn.WbRegID}"')
            continue
        # Если ттнка есть в списке ранее принятых накладных
        if RN_ttn.WbRegID in accepted_ttns:
            shipper_info = get_shipper_info(RN_ttn.Shipper)
            text = f"Данная накладная уже принята✅\n"
            if shipper_info is None:
                text += f"Поставщик: <code>{RN_ttn.Shipper}</code>\n"
            else:
                text += f"Поставщик: <code>{shipper_info.name}</code>\n"
            text += (
                f"Дата: <code>{RN_ttn.ttnDate}</code>\n"
                f"ТТН-ЕГАИС: <code>{RN_ttn.WbRegID}</code>\n"
            )
            await call.message.answer(text)
            log_e.debug(f'Данная накладная уже принята "{RN_ttn.WbRegID}"')
            continue

        shipper_info = get_shipper_info(RN_ttn.Shipper)
        text = f"<b>Перевысылаю накладную #️⃣{count}</b>\n"
        if shipper_info is None:
            text += f"Поставщик: <code>{RN_ttn.Shipper}</code>\n"
        else:
            text += f"Поставщик: <code>{shipper_info.name}</code>\n"
        text += (
            f"Дата: <code>{RN_ttn.ttnDate}</code>\n"
            f"ТТН-ЕГАИС: <code>{RN_ttn.WbRegID}</code>\n"
        )

        await call.message.answer(text)
        await utm.send_QueryResendDoc(wb.fsrar, RN_ttn.WbRegID)
        await create_ttn_log(
            cash_number=cash.shopcode,
            user_id=call.message.chat.id,
            level="SUCCES",
            type="Перевыслать",
            inn=wb.inn,
            shipper_fsrar=RN_ttn.Shipper,
            ttns_egais=RN_ttn.WbRegID,
            description="Перевыслают автоматически",
        )
        if count != len(RN_ttns):
            await call.message.answer(
                "Следующая накладная автоматически будет перевыслана через 10 минут, вам ничего делать не нужно.\n"
                "По правилам ЕГАИС, можно перевысылать 1 накладную раз в 10 минут"
            )
            await asyncio.sleep(60 * 11)
    await call.message.answer("Переотправка накладных завершена.✅")


async def start_resend_ttn_from_text(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    await state.set_state(ResendTTNfromText.enter_ttnEgais)
    log_e.button("Ввести номер ТТН в ручную")
    await call.message.edit_text(
        "Напишите номер ТТН ЕГАИС от накладной. Номер начинается на 0 (Ноль) и состоит из 10 цифр\n"
        "Если поставщик - <b><u>Алкоторг</u></b>, то номер ТТН ЕГАИС указан в бумажной накладной. Иначе звоните поставщику и узнавайте номер ТТН ЕГАИС"
    )


async def end_resend_ttn_from_text(
    message: Message, state: FSMContext, log_e: LoggerEGAIS
):
    ttns = message.text.split()
    data = await state.get_data()
    wb = Waybills.model_validate_json(data.get("wb"))
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    await message.answer(texts.load_information)
    utm = UTM(ip=cash.ip(), port=wb.port)
    for ttn in ttns:
        if not re.findall(r"^\d{10}$", ttn) and not re.findall(r"TTN-\d{10}", ttn):
            text = (
                f'В вашем номере "{ttn}" не найдено ТТН ЕГАИС\n'
                f"1) Номер должен начинатся на 0 (Ноль) и состоять из 10 цифр\n"
                f"2) Если поставщик - <b><u>Алкоторг</u></b>, то номер ТТН ЕГАИС указан в бумажной накладной. Иначе звоните поставщику и узнавайте номер ТТН ЕГАИС\n"
                f"Пример: <b><u>0770328186</u></b>\n"
                f"Попробуйте снова."
            )
            await message.answer(texts.error_head + text)
            return
    if not await check_recent_tickets(utm):
        log_e.error(
            "Попытка перевыслать накладную была предпринята в последние 10 минут"
        )
        text = (
            "Попытка перевыслать накладную была предпринята в последние 10 минут.\n"
            "Повторная попытка будет доступна через 10 минут."
        )
        msg = await texts.error_message_wp(cash, text)
        await message.answer(texts.error_head + text, reply_markup=kb_whatsapp_url(msg))
        return
    WB_ttns = await utm.get_Waybill_and_FORM2REGINFO()
    for count, ttn in enumerate(ttns, 1):
        # Если есть накладная, то пишет что она есть
        count_ttn_in_utm = 0
        for ttn_in_utm in WB_ttns:
            if ttn_in_utm.ttn_egais.split("-")[1] == ttn:
                count_ttn_in_utm += 1

        if count_ttn_in_utm > 0:
            text = (
                "<b>Данная накладная уже загружена на кассу</b>\n"
                f"ТТН-ЕГАИС: <code>{ttn}</code>\n"
            )
            await message.answer(text)
            log_e.debug(f'Данная накладная уже загружена на кассу "{ttn}"')
            continue

        text = (
            f"<b>Перевысылаю накладную #️⃣{count}</b>\n"
            f"ТТН-ЕГАИС: <code>{ttn}</code>\n"
        )

        await message.answer(text)
        await utm.send_QueryResendDoc(wb.fsrar, f"TTN-{ttn}")
        await create_ttn_log(
            cash_number=cash.shopcode,
            user_id=message.chat.id,
            level="SUCCES",
            type="Перевыслать",
            inn=wb.inn,
            ttns_egais=ttn,
            description="Перевысылают в ручную",
        )
        if count != len(ttns):
            await message.answer(
                "Следующая накладная автоматически будет перевыслана через 10 минут, вам ничего делать не нужно.\n"
                "По правилам ЕГАИС, можно перевысылать 1 накладную раз в 10 минут"
            )
            await asyncio.sleep(60 * 11)
    await message.answer("Переотправка накладных завершена.✅")
    # await state.clear()
    # await state.update_data(foreman_cash=cash.model_dump_json(by_alias=True))


async def resend_simple_ttn(
    call: CallbackQuery, state: FSMContext, callback_data: ResendTTN, log_e: LoggerEGAIS
):
    data = await state.get_data()
    wb = Waybills.model_validate_json(data.get("wb"))
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    utm = UTM(ip=cash.ip(), port=wb.port)
    if not await check_recent_tickets(utm):
        log_e.error(
            "Попытка перевыслать накладную была предпринята в последние 10 минут"
        )
        text = (
            "Попытка перевыслать накладную была предпринята в последние 10 минут.\n"
            "Повторная попытка будет доступна через 10 минут."
        )
        msg = await texts.error_message_wp(cash, text)
        await call.message.answer(
            texts.error_head + text, reply_markup=kb_whatsapp_url(msg)
        )
        return
    text = (
        f"<b>Перевысылаю накладную, накладная появится в течении 5-10 минут</b>\n"
        f"ТТН-ЕГАИС: <code>{callback_data.ttn_egais}</code>\n"
    )
    await call.message.answer(text)
    await utm.send_QueryResendDoc(wb.fsrar, callback_data.ttn_egais)
    await create_ttn_log(
        cash_number=cash.shopcode,
        user_id=call.message.chat.id,
        level="SUCCES",
        type="Перевыслать",
        inn=wb.inn,
        ttns_egais=callback_data.ttn_egais,
        shipper_inn=callback_data.shipper_inn,
        description="Перевысылают из списка",
    )
    await call.answer()
