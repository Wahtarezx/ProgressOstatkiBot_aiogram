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
from core.database.query_BOT import create_goods_log, save_onlinecheck
from core.keyboards import inline
from core.keyboards.reply import one_time_scanner
from core.loggers.egais_logger import LoggerEGAIS
from core.services.egais.TTN.accept import read_barcodes_from_image
from core.services.egais.goods.create_barcodes import read_datamatrix_from_image
from core.services.egais.goods.pd_models import TmcType, OpMode
from core.services.egais.states import DegustationState
from core.utils import texts
from core.utils.CS.cs import CS
from core.utils.CS.pd_onlinecheck import OnlineCheck, DegustationGood, Degustation
from core.utils.foreman.pd_model import ForemanCash
from core.utils.qr import get_buffer_qr

router = Router()


@router.callback_query(F.data == "online_checks")
async def online_checks(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Онлайн чеки")
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    await call.message.edit_text(
        "Выберите действие", reply_markup=inline.kb_online_checks(cash)
    )


@router.callback_query(F.data == "online_check_degustation")
async def start_scan_bcode(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Дегустация")
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    artix = ArtixCashDB(cash.ip())
    valut = await artix.get_valut_by_name("дегустация")
    if valut is None:
        log_e.error('Валюта "дегустация" не найдена')
        msg = 'Нужно на кассе создать способ оплаты "Дегустация"'
        await call.message.answer(
            texts.error_head + msg, reply_markup=inline.kb_whatsapp_url(msg)
        )
        return
    await state.set_state(DegustationState.bcode)
    await call.message.delete()
    await call.message.answer(texts.scan_photo_or_text, reply_markup=one_time_scanner())


@router.message(
    DegustationState.bcode,
    F.content_type.in_(
        [
            ContentType.PHOTO,
            ContentType.DOCUMENT,
            ContentType.WEB_APP_DATA,
            ContentType.TEXT,
        ]
    ),
)
async def get_barcode(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    msg = "Введите цифры акцизной марки"
    if message.photo is None and message.document is None:
        if message.web_app_data is not None:
            log_e.debug(message.web_app_data.data)
            barcode = message.web_app_data.data
            log_e.info(f'Отсканировал сканером штрихкод "{barcode}"')
        else:
            barcode = message.text
            if not barcode.isdigit():
                msg = "Штрихкод должен состоять только из цифр"
                log_e.error(f'Штрихкод не только из цифр "{barcode}"')
                await message.answer(
                    texts.error_head + msg, reply_markup=inline.kb_whatsapp_url(msg)
                )
                return
            log_e.info(f'Написали штрихкод(-а) "{barcode}"')
    else:
        log_e.info("Начал сканирование фото")
        barcode = await get_barcodes_from_photo(message, log_e)
        if barcode is None:
            return

    degustation = DegustationGood(bcode=barcode)
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    artix = ArtixCashDB(cash.ip())
    tmc = await artix.get_tmc(barcode)
    if tmc is not None:
        log_e.info(f'Найден товар на кассе с названием "{tmc.name}"')
        degustation.name = tmc.name
        await state.set_state(DegustationState.amark)
        await message.bot.send_photo(
            message.chat.id,
            photo=FSInputFile(str(Path(config.dir_path, "files", "example_amark.png"))),
            caption=msg,
        )
    else:
        await message.answer(
            "Напишите ответным сообщением <b>название товара</b>",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.set_state(DegustationState.name)

    await state.update_data(degustation_good=degustation.model_dump_json())


@router.message(DegustationState.name)
async def get_name(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.info(f'Ввели название "{message.text}"')
    data = await state.get_data()
    degustation_good = DegustationGood.model_validate_json(data.get("degustation_good"))
    degustation_good.name = message.text
    await state.update_data(degustation_good=degustation_good.model_dump_json())
    await state.set_state(DegustationState.amark)
    await message.bot.send_photo(
        message.chat.id,
        photo=FSInputFile(str(Path(config.dir_path, "files", "example_amark.png"))),
        caption="Напишите ответным сообщением <b>акцизную марку</b>",
    )


@router.message(DegustationState.amark)
async def get_amark(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.info(f'Ввели акцизную марку "{message.text}"')
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    artix = ArtixCashDB(cash.ip())
    find_amark = await artix.get_excise_from_whitelist(message.text)
    if find_amark is None:
        msg = f'Акцизная марка "{message.text}" не найдена, или отсутствует в белом списке на кассе'
        log_e.error(msg)
        await message.answer(
            texts.error_head + msg, reply_markup=inline.kb_whatsapp_url(msg)
        )
        return

    log_e.info(f'Акцизная марка "{find_amark.excisemarkid}" найдена')
    data = await state.get_data()
    degustation_good = DegustationGood.model_validate_json(data.get("degustation_good"))
    if data.get("degustation"):
        degustation = Degustation.model_validate_json(data.get("degustation"))
        if find_amark.excisemarkid in [g.amark for g in degustation.goods]:
            msg = (
                "Акцизная марка уже есть в дегустации.\n"
                "Напишите ответным сообщением новую марку"
            )
            log_e.error(
                f'Акцизная марка "{find_amark.excisemarkid}" уже есть в дегустации'
            )
            await message.answer(
                texts.error_head + msg, reply_markup=inline.kb_whatsapp_url(msg)
            )
            return
    degustation_good.amark = find_amark.excisemarkid
    await state.update_data(degustation_good=degustation_good.model_dump_json())
    await state.set_state(DegustationState.price)
    await message.answer("Напишите цену бутылки")


@router.message(DegustationState.price)
async def price(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    price = message.text.replace(",", ".")
    check_price = price.replace(".", "")
    if not check_price.isdecimal():
        msg = (
            "Цена должна состоять только из цифр\n"
            "Напишите еще раз ответным сообщением <b>цену бутылки</b>"
        )
        log_e.error(f'Цена "{price}" должна состоять только из цифр')
        await message.answer(
            texts.error_head + msg, reply_markup=inline.kb_whatsapp_url(msg)
        )
        return
    log_e.info(f'Ввели цену бутылки "{price}"')
    data = await state.get_data()
    degustation_good = DegustationGood.model_validate_json(data.get("degustation_good"))
    degustation_good.price = price
    if data.get("degustation") is not None:
        degustation = Degustation.model_validate_json(data.get("degustation"))
        degustation.goods.append(degustation_good)
    else:
        degustation = Degustation()
        degustation.goods.append(degustation_good)
    await state.update_data(degustation=degustation.model_dump_json())
    await state.set_state(DegustationState.prepare_commit)
    prepare_text = degustation.prepare_text()
    log_e.info(degustation.model_dump_json())
    for i, text in enumerate(prepare_text, start=1):
        if i == len(prepare_text):
            await message.answer(
                text, reply_markup=inline.kb_degustation_prepare_commit()
            )
        else:
            await message.answer(text)


@router.callback_query(F.data == "commit_degustation")
async def mail(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Готова дегустация")
    await call.message.edit_text("Напишите электронную почту клиента")
    await state.set_state(DegustationState.mail)


@router.message(DegustationState.mail)
async def mail_and_commit(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    email = message.text
    if "@" not in email:
        msg = (
            'Электронная почта должна содержать "@"\n'
            "Напишите еще раз ответным сообщением <b>электронную почту клиента</b>"
        )

        log_e.error(f'Неверная электронная почта "{email}"')
        await message.answer(
            texts.error_head + msg, reply_markup=inline.kb_whatsapp_url(msg)
        )
        return

    log_e.info(f'Ввели электронную почту "{email}"')

    data = await state.get_data()
    degustation = Degustation.model_validate_json(data.get("degustation"))
    degustation.email = email

    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    artix = ArtixCashDB(cash.ip())
    valut = await artix.get_valut_by_name("дегустация")

    onlinecheck_document = degustation.onlinecheck_document(valut)
    onlinecheck = OnlineCheck(
        shopcode=cash.shopcode,
        cashcode=cash.cashcode,
        document=onlinecheck_document.model_dump_json(),
    )

    cs = CS()
    cs_onlinecheck = await cs.create_onlinecheck(onlinecheck)
    await save_onlinecheck(
        csid=cs_onlinecheck.get("id"),
        user_id=str(message.from_user.id),
        shopcode=cash.shopcode,
        cashcode=cash.cashcode,
        documentid=onlinecheck.documentid,
        type=OnlineCheckType.DEGUSTATION,
    )

    with open(
        cash.onlinechecks_file_path(f"check-{onlinecheck.documentid}.json"),
        "w",
        encoding="utf-8",
    ) as f:
        oc_model = {
            "documentid": f"check-{onlinecheck.documentid}",
            "email": degustation.email,
        }
        json.dump(oc_model, f, ensure_ascii=False, indent=4)
    for i, text in enumerate(degustation.prepare_text(), start=1):
        if i == 1:
            await message.bot.send_photo(
                message.chat.id,
                photo=BufferedInputFile(
                    await get_buffer_qr(f"check-{onlinecheck.documentid}"),
                    filename=f"check-{onlinecheck.documentid}.png",
                ),
                caption=(
                    f"<b>Онлайн-чек</b>: <code>{onlinecheck.documentid}</code>\n{text}"
                ),
            )
        else:
            await message.answer(text)
    log_e.success(f'Создан онлайн-чек дегустации: "{onlinecheck.documentid}"')
    await state.update_data(degustation=None, degustation_good=None)


async def get_barcodes_from_photo(message: Message, log_e: LoggerEGAIS) -> str | None:
    barcode_path = Path(config.dir_path, "files", "", str(message.chat.id))
    barcode_path.mkdir(parents=True, exist_ok=True)
    if message.photo is not None:
        img = await message.bot.get_file(message.photo[-1].file_id)
    elif message.document is not None:
        img = await message.bot.get_file(message.document.file_id)
    file = barcode_path / f"barcode_{message.message_id}.jpg"
    await message.bot.download_file(img.file_path, file)
    log_e.info("Начал сканирование фото")
    barcodes_from_img = await read_datamatrix_from_image(file)
    if not barcodes_from_img:
        barcodes_from_img += await read_barcodes_from_image(file)
    log_e.info(f'Отсканировал фото "{barcodes_from_img}"')
    try:
        if len(barcodes_from_img) == 0:  # Если не нашлись штрихкода на картинке
            msg = "На данном фото <b><u>не найдено</u></b> штрихкода"
            await message.bot.send_photo(
                message.chat.id, photo=FSInputFile(file), caption=msg
            )
            log_e.debug(msg)
            file.unlink(missing_ok=True)
            raise ValueError(msg)
        elif len(barcodes_from_img) > 1:
            msg = "На данном фото найдено <b><u>несколько</u></b> штрихкодов"
            await message.bot.send_photo(
                message.chat.id, photo=FSInputFile(file), caption=msg
            )
            log_e.debug(msg)
            file.unlink(missing_ok=True)
            raise ValueError(msg)
    except ValueError as v:
        log_e.error(str(v))
        return

    file.unlink(missing_ok=True)

    return barcodes_from_img
