import json
from pathlib import Path

from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    FSInputFile,
    CallbackQuery,
    ReplyKeyboardRemove,
    BufferedInputFile,
)

import config
from core.database.artix.querys import ArtixCashDB
from core.database.modelBOT import OnlineCheckType
from core.database.query_BOT import save_onlinecheck
from core.keyboards import inline
from core.keyboards.reply import one_time_scanner
from core.loggers.egais_logger import LoggerEGAIS
from core.services.egais.goods.pd_models import Measure, Dcode, TmcType
from core.services.egais.online_checks.states import OnlineChecksBasicState
from core.services.egais.states import DegustationState
from core.services.markirovka.callbackdata import cbValut
from core.services.markirovka.trueapi import TrueApi
from core.utils import texts
from core.utils.CS.cs import CS
from core.utils.CS.pd_onlinecheck import (
    OnlineCheck,
    DegustationGood,
    Degustation,
    Document,
    OcPosition,
    Payments,
)
from core.utils.foreman.pd_model import ForemanCash
from core.utils.qr import get_buffer_qr
from core.utils.znak.pd_model import BarcodeType
from core.utils.znak.scanner import Scanner, get_ean_from_gtin

router = Router()


async def is_duplicate_mark(basic_document: Document, mark: str) -> bool:
    return any(mark == o.excisemark for o in basic_document.positions)


@router.callback_query(F.data == "onlinecheck_basic_duplicate_position")
async def onlinecheck_basic_duplicate_position(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    log_e.button("Список сканированных товаров")
    data = await state.get_data()
    basic_document = Document.model_validate_json(data.get("basic_document"))
    await state.set_state(OnlineChecksBasicState.prepare_commit)
    prepare_text = await basic_document.prepare_text()
    if len(prepare_text) == 1:
        await call.message.edit_text(
            prepare_text[0], reply_markup=inline.kb_onlinecheck_basic_prepare_commit()
        )
    else:
        await call.message.delete()
        for i, text in enumerate(prepare_text, start=1):
            if i == len(prepare_text):
                await call.message.answer(
                    text, reply_markup=inline.kb_onlinecheck_basic_prepare_commit()
                )
            else:
                await call.message.answer(text)


@router.callback_query(F.data == "online_check_basic")
async def online_check_basic(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    log_e.button("Сформировать чек")
    data = await state.get_data()
    await state.set_state(OnlineChecksBasicState.scan_or_photo)
    if data.get("basic_document") is not None:
        basic_document = Document.model_validate_json(data.get("basic_document"))
        await state.set_state(OnlineChecksBasicState.prepare_commit)
        prepare_text = await basic_document.prepare_text()
        if len(prepare_text) == 1:
            await call.message.edit_text(
                prepare_text[0],
                reply_markup=inline.kb_onlinecheck_basic_prepare_commit(),
            )
        else:
            await call.message.delete()
            for i, text in enumerate(prepare_text, start=1):
                if i == len(prepare_text):
                    await call.message.answer(
                        text, reply_markup=inline.kb_onlinecheck_basic_prepare_commit()
                    )
                else:
                    await call.message.answer(text)
    else:
        await call.message.delete()
        await call.message.answer(
            texts.scan_datamatrix_photo, reply_markup=one_time_scanner()
        )


@router.callback_query(F.data == "online_check_basic_more_position")
async def online_check_basic_more_position(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    log_e.button("Добавить позицию")
    await call.message.delete()
    await call.message.answer(
        texts.scan_datamatrix_photo, reply_markup=one_time_scanner()
    )
    await state.set_state(OnlineChecksBasicState.scan_or_photo)


@router.message(OnlineChecksBasicState.scan_or_photo)
async def scan_or_photo(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    dir_photo = Path(config.dir_path, "files", "onlinechecks", "basic")
    scanner = Scanner(dir_photo)
    barcodes = await scanner.get_barcodes_from_message(message, log_e)
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))

    if len(barcodes) == 0:
        await message.answer(
            "Не обнаружено ни одного штрихкода\n" "Повторите попытку",
            reply_markup=one_time_scanner(),
        )
        log_e.error("Не обнаружено ни одного штрихкода")
        return
    elif len(barcodes) > 1:
        await message.answer(
            "Найдено более одного штрихкода\n" "Повторите попытку",
            reply_markup=one_time_scanner(),
        )
        log_e.error("Найдено более одного штрихкода")
        return

    barcode_info = (await scanner.get_type_barcode(barcodes))[0]
    if barcode_info.type == BarcodeType.DATAMATRIX:
        if data.get("basic_document") is not None:
            basic_document = Document.model_validate_json(data.get("basic_document"))
            if await is_duplicate_mark(basic_document, barcode_info.value):
                await message.answer(
                    texts.error_head + "Данная позиция уже есть в чеке",
                    reply_markup=inline.kb_onlinecheck_basic_dublicate_position(),
                )
                log_e.error("Данная позиция уже есть в чеке")
                return
        znak = TrueApi(inn_to_auth=config.main_inn)
        await znak.create_token()
        cis_info = await znak.get_cises_info([barcode_info.value.split("\x1d")[1]])

        ean = await get_ean_from_gtin(cis_info[0].cisInfo.gtin)
        if cis_info[0].cisInfo.productName is not None:
            name = cis_info[0].cisInfo.productName
            log_e.info(f'Установил название товара из ЧЗ "{name}"')
        else:
            artix = ArtixCashDB(cash.ip())
            tmc = await artix.get_tmc(ean)
            if tmc is not None:
                name = tmc.name
                log_e.info(f'Установил название товара из бд кассы "{name}"')
            else:
                log_e.info(f'Не нашел названия товара "{ean}" в БД кассы и в ЧЗ')
                name = ""
        basic_position = OcPosition(
            code=ean,
            barcode=ean,
            name=name,
            price=0,
            quant=1,
            measure=Measure.unit.value,
            dept=Dcode.markirovka,
            tmctype=TmcType.markedgoods.name,
            excisemark=barcode_info.value,
        )
        if name:
            await state.set_state(OnlineChecksBasicState.product_price)
            await message.answer(
                "Напишите ответным сообщением <b>стоимость товара</b>",
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            await state.set_state(OnlineChecksBasicState.product_name)
            await message.answer(
                "Напишите ответным сообщением <b>название товара</b>",
                reply_markup=ReplyKeyboardRemove(),
            )
        await state.update_data(basic_position=basic_position.model_dump_json())
    elif barcode_info.type == BarcodeType.BARCODE:
        artix = ArtixCashDB(cash.ip())
        tmc = await artix.get_tmc(barcode_info.value)
        barcode = await artix.get_barcode(barcode_info.value)
        if barcode is None or tmc is None:
            await message.answer(
                f"Штрихкод <code>{barcode_info.value}</code> не найден кассе\n"
                f"Добавьте товар на кассу и попробуйте снова.",
                reply_markup=inline.kb_onlinecheck_add_good(),
            )
            return
        measure = await artix.get_unit(barcode.measure)
        basic_position = OcPosition(
            code=tmc.code,
            barcode=tmc.bcode,
            name=barcode.name,
            price=0,
            quant=1,
            measure=barcode.measure,
            measurename=measure.name,
            isfractionalmeasure=measure.flag,
            minprice=barcode.minprice,
            dept=tmc.dcode,
            tmctype=TmcType(barcode.tmctype).name,
        )
        if TmcType(barcode.tmctype) in [
            TmcType.markedgoods,
            TmcType.tobacco,
            TmcType.shoes,
            TmcType.protectivemeans,
            TmcType.medicinal,
            TmcType.draftbeer,
        ]:
            await message.answer(texts.scan_datamatrix_photo)
            await state.set_state(OnlineChecksBasicState.product_markirovka)
        elif TmcType(barcode.tmctype) == TmcType.alcohol:
            await message.bot.send_photo(
                message.chat.id,
                photo=FSInputFile(
                    path=Path(config.dir_path, "files", "example_amark.png")
                ),
                caption="Введите цифры акцизной марки",
            )
            await state.set_state(OnlineChecksBasicState.product_excisemark)
        elif TmcType(barcode.tmctype) == TmcType.basic:
            await state.set_state(OnlineChecksBasicState.product_price)
            await message.answer(
                "Напишите ответным сообщением <b>стоимость товара</b>",
                reply_markup=ReplyKeyboardRemove(),
            )
        await state.update_data(basic_position=basic_position.model_dump_json())
    elif barcode_info.type == BarcodeType.UNKNOWN:
        msg = (
            f"Неизвестный тип штрихкода <code>{barcode_info.value}</code>\n"
            f"Попробуйте отсканировать снова, или обратитесь в службу поддержки"
        )
        await message.answer(
            texts.error_head + msg, reply_markup=inline.kb_whatsapp_url(msg)
        )
        log_e.error(msg)


@router.message(OnlineChecksBasicState.product_markirovka)
async def product_markirovka(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    scanner = Scanner(Path(config.dir_path, "files", "onlinechecks", "basic"))
    barcodes = await scanner.get_barcodes_from_message(message, log_e)

    if len(barcodes) == 0:
        await message.answer(
            "Не обнаружено ни одного штрихкода\n" "Повторите попытку",
            reply_markup=one_time_scanner(),
        )
        log_e.error("Не обнаружено ни одного штрихкода")
        return
    elif len(barcodes) > 1:
        await message.answer(
            "Найдено более одного штрихкода\n" "Повторите попытку",
            reply_markup=one_time_scanner(),
        )
        log_e.error("Найдено более одного штрихкода")
        return

    barcode_info = (await scanner.get_type_barcode(barcodes))[0]
    if barcode_info.type == BarcodeType.DATAMATRIX:
        basic_position = OcPosition.model_validate_json(data.get("basic_position"))
        basic_position.excisemark = barcode_info.value
        await state.update_data(basic_position=basic_position.model_dump_json())
        await state.set_state(OnlineChecksBasicState.product_price)
        await message.answer(
            "Напишите ответным сообщением <b>стоимость товара</b>",
            reply_markup=ReplyKeyboardRemove(),
        )
    elif barcode_info.type == BarcodeType.BARCODE:
        msg = (
            f"Вы отсканировали штрихкод <code>{barcode_info.value}</code>\n"
            f"Попробуйте отсканировать маркировку снова, или обратитесь в службу поддержки"
        )
        log_e.info(f'Отсканировал штрихкод "{barcode_info.value}"')
        await message.answer(
            texts.error_head + msg, reply_markup=inline.kb_whatsapp_url(msg)
        )
        log_e.error(msg)
    elif barcode_info.type == BarcodeType.UNKNOWN:
        msg = (
            f"Неизвестный тип штрихкода <code>{barcode_info.type}</code>\n"
            f"Попробуйте отсканировать снова, или обратитесь в службу поддержки"
        )
        await message.answer(
            texts.error_head + msg, reply_markup=inline.kb_whatsapp_url(msg)
        )
        log_e.error(msg)


@router.message(OnlineChecksBasicState.product_price)
async def product_price(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    price = message.text.replace(",", ".")
    if not price.replace(".", "", 1).isdigit():
        msg = (
            f"Некорректная цена <code>{price}</code>\n"
            f"Попробуйте снова отправить цену, или обратитесь в службу поддержки"
        )
        await message.answer(msg, reply_markup=inline.kb_whatsapp_url(msg))
        log_e.error(f"Некорректная цена <code>{price}</code>")
        return

    log_e.info(f'Написали цену "{price}"')
    basic_position = OcPosition.model_validate_json(data.get("basic_position"))
    basic_position.price = float(price)

    if data.get("basic_document") is not None:
        basic_document = Document.model_validate_json(data.get("basic_document"))
        basic_document.positions.append(basic_position)
    else:
        basic_document = Document(positions=[basic_position])

    await state.update_data(basic_document=basic_document.model_dump_json())
    await state.set_state(OnlineChecksBasicState.prepare_commit)
    log_e.debug(basic_document.model_dump_json())
    prepare_text = await basic_document.prepare_text()
    if len(prepare_text) == 1:
        await message.answer(
            prepare_text[0], reply_markup=inline.kb_onlinecheck_basic_prepare_commit()
        )
    else:
        for i, text in enumerate(prepare_text, start=1):
            if i == len(prepare_text):
                await message.answer(
                    text, reply_markup=inline.kb_onlinecheck_basic_prepare_commit()
                )
            else:
                await message.answer(text)


@router.message(OnlineChecksBasicState.product_excisemark)
async def product_excisemark(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    artix = ArtixCashDB(cash.ip())
    whitelist_amark = await artix.get_excise_from_whitelist(message.text)
    if whitelist_amark is None:
        msg = (
            f"Не найдено акцизной марки в белом списке <code>{message.text}</code>\n"
            f"Попробуйте снова отправить марку, или обратитесь в службу поддержки"
        )
        await message.answer(msg, reply_markup=inline.kb_whatsapp_url(msg))
        log_e.error(f"Не найдено акцизной марки в белом списке {message.text}")
        return
    if data.get("basic_document") is not None:
        basic_document = Document.model_validate_json(data.get("basic_document"))
        if await is_duplicate_mark(basic_document, whitelist_amark.excisemarkid):
            await message.answer(
                texts.error_head + "Данная позиция уже есть в чеке",
                reply_markup=inline.kb_onlinecheck_basic_dublicate_position(),
            )
            log_e.error("Данная позиция уже есть в чеке")
            return
    basic_position = OcPosition.model_validate_json(data.get("basic_position"))
    basic_position.excisemark = whitelist_amark.excisemarkid
    await state.update_data(basic_position=basic_position.model_dump_json())
    await state.set_state(OnlineChecksBasicState.product_price)
    await message.answer(
        "Напишите ответным сообщением <b>стоимость</b> товара",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(OnlineChecksBasicState.product_name)
async def product_name(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    name = message.text
    if name.isdigit():
        msg = (
            f"Некорректное название <code>{name}</code>\n"
            f"Попробуйте снова отправить <b>название</b>, или обратитесь в службу поддержки"
        )
        await message.answer(msg, reply_markup=inline.kb_whatsapp_url(msg))
        log_e.error(f"Некорректное название <code>{name}</code>")
        return
    log_e.info(f'Написали название "{name}"')
    basic_position = OcPosition.model_validate_json(data.get("basic_position"))
    basic_position.name = name
    await state.update_data(basic_position=basic_position.model_dump_json())
    await state.set_state(OnlineChecksBasicState.product_price)
    await message.answer(
        "Напишите ответным сообщением <b>стоимость товара</b>",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.callback_query(
    F.data == "onlinecheck_basic_payment", OnlineChecksBasicState.prepare_commit
)
async def onlinecheck_basic_payment(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    artix = ArtixCashDB(cash.ip())
    valutes = await artix.get_all_valuts()
    await state.set_state(OnlineChecksBasicState.payment)
    await call.message.edit_text(
        "Выберите валюту", reply_markup=inline.kb_valutes(valutes)
    )


@router.callback_query(cbValut.filter(), OnlineChecksBasicState.payment)
async def select_basic_payment(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS, callback_data: cbValut
):
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    artix = ArtixCashDB(cash.ip())
    valute = await artix.get_valut(callback_data.code)

    basic_document = Document.model_validate_json(data.get("basic_document"))
    payment = Payments(
        type=valute.type,
        valcode=valute.code,
        amount=basic_document.sum,
        valname=valute.name,
    )
    basic_document.payments = [payment]

    onlinecheck = OnlineCheck(
        shopcode=cash.shopcode,
        cashcode=cash.cashcode,
        document=basic_document.model_dump_json(),
    )

    cs = CS()
    cs_onlinecheck = await cs.create_onlinecheck(onlinecheck)
    await save_onlinecheck(
        csid=cs_onlinecheck.get("id"),
        user_id=str(call.message.chat.id),
        shopcode=cash.shopcode,
        cashcode=cash.cashcode,
        documentid=onlinecheck.documentid,
        type=OnlineCheckType.BASIC,
    )
    await call.message.delete()
    for i, text in enumerate(await basic_document.prepare_text(), start=1):
        if i == 1:
            await call.message.bot.send_photo(
                call.message.chat.id,
                photo=BufferedInputFile(
                    await get_buffer_qr(f"check-{onlinecheck.documentid}"),
                    filename=f"check-{onlinecheck.documentid}.png",
                ),
                caption=(
                    f"<b>Онлайн-чек</b>: <code>{onlinecheck.documentid}</code>\n{text}"
                ),
            )
        else:
            await call.message.answer(text)
    log_e.success(f'Сформирован онлайн-чек: "{onlinecheck.documentid}"')
    await state.update_data(
        basic_document=None,
        basic_position=None,
    )
