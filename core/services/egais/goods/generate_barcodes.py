import asyncio
import os
import re

import sqlalchemy.exc
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, FSInputFile, ReplyKeyboardRemove

import config
from core.cron.barcodes import add_barcodes_in_cash
from core.database.query_BOT import create_goods_log, get_barcodes_for_add
from core.keyboards.inline import (
    kb_genbcode_select_dcode,
    kb_genbcode_select_measure_alcohol,
    kb_genbcode_select_measure_beer,
    kb_genbcode_select_measure_products,
    kb_whatsapp_url,
)
from core.keyboards.reply import one_time_scanner
from core.loggers.egais_logger import LoggerEGAIS
from core.services.egais.TTN.accept import read_barcodes_from_image, check_file_exist
from core.services.egais.logins.pd_models import Cash
from core.utils import texts
from core.utils.callbackdata import SelectDcode, SelectMeasure
from core.utils.foreman.pd_model import ForemanCash
from core.utils.generateBarcode import generate_barcode, generate_pdf
from core.utils.states import GenerateBarcode


async def select_dcode(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Сгенерировать штрихкод")
    await call.message.edit_text(
        "Выберите нужный тип товара", reply_markup=kb_genbcode_select_dcode()
    )
    await state.set_state(GenerateBarcode.dcode)
    await state.update_data(barcode=None)


async def select_measure(
    call: CallbackQuery,
    bot: Bot,
    state: FSMContext,
    callback_data: SelectDcode,
    log_e: LoggerEGAIS,
):
    await state.set_state(GenerateBarcode.measure)
    dcode, op_mode, tmctype = (
        callback_data.dcode,
        callback_data.op_mode,
        callback_data.tmctype,
    )
    log_e.info(f"Выбрали dcode={dcode}")
    await state.update_data(dcode=dcode, op_mode=op_mode, tmctype=tmctype)
    if dcode == 1:
        await call.message.edit_text(
            "Выберите вид продажи\n"
            "<b><u>Поштучный</u></b> - Алкоголь который будете продавать сканировав акцизную марку\n"
            "<b><u>Розлив</u></b> - Алкоголь который продаётся порционно (подойдет для баров)",
            reply_markup=kb_genbcode_select_measure_alcohol(),
        )
    elif dcode == 2:
        await call.message.edit_text(
            "Выберите вид продажи\n"
            "<b><u>Поштучный</u></b> - Пиво которое будете продавать целыми бутылками или банками\n"
            "<b><u>Розлив</u></b> - Пиво которое продаётся порционно (подойдет для пива которое в кегах)",
            reply_markup=kb_genbcode_select_measure_beer(),
        )
    elif dcode == 3:
        await state.update_data(measure=1)
        await state.set_state(GenerateBarcode.barcode)
        await bot.send_message(
            call.message.chat.id,
            texts.scan_photo_or_text,
            reply_markup=one_time_scanner(),
        )
    elif dcode == 4:
        await call.message.edit_text(
            "Выберите вид продажи\n"
            "<b><u>Поштучный</u></b> - Товар который будет продаваться целиком. Например: консерва, шоколад, колбаса\n"
            "<b><u>Весовой</u></b> - Товар который продаётся порционно. Например: Сыр, рыба, орехи\n"
            "<b><u>Розлив</u></b> - Товар который продаётся порционно. Например: Разливной лимонад",
            reply_markup=kb_genbcode_select_measure_products(),
        )
    elif dcode == 5:
        await state.update_data(measure=1)
        await state.set_state(GenerateBarcode.barcode)
        await bot.send_message(
            call.message.chat.id,
            texts.scan_photo_or_text,
            reply_markup=one_time_scanner(),
        )


async def accept_measure(
    call: CallbackQuery,
    bot: Bot,
    state: FSMContext,
    callback_data: SelectMeasure,
    log_e: LoggerEGAIS,
):
    data = await state.get_data()
    measure, op_mode, tmctype, dcode = (
        callback_data.measure,
        callback_data.op_mode,
        callback_data.tmctype,
        data["dcode"],
    )
    await state.update_data(
        measure=measure,
        op_mode=op_mode,
        tmctype=tmctype,
        qdefault=callback_data.qdefault,
    )
    log_e.info(
        f"Выбрали measure={measure} op_mode={op_mode} tmctype={tmctype} qdefault={callback_data.qdefault}"
    )
    if (
        (dcode == 1 and tmctype == 1)
        or (dcode == 2 and measure == 1)
        or (dcode == 4 and measure == 1)
    ):
        await state.set_state(GenerateBarcode.barcode)
        await bot.send_message(
            call.message.chat.id,
            texts.scan_photo_or_text,
            reply_markup=one_time_scanner(),
        )
    else:
        await state.set_state(GenerateBarcode.price)
        await call.message.edit_text("Напишите цену товара")


async def text_barcode(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    if message.web_app_data is not None:

        def clean_and_decode(value):
            cleaned_value = value.replace("\x1d", "")
            if "\\u" in cleaned_value:
                decoded_value = cleaned_value.encode("utf-8").decode("unicode_escape")
            else:
                decoded_value = cleaned_value
            return decoded_value

        text = clean_and_decode(message.web_app_data.data).strip()
        log_e.info(f'Отсканировал сканером штрихкод "{text}"')
    else:
        text = message.text
        log_e.info(f'Написали штрихкод(-а) "{text}"')

    if not text.isdigit():
        log_e.error(f'Штрихкод состоит не из цифр "{text}"')
        await message.answer(
            texts.error_head
            + "Штрихкод состоит только из цифр.\nВведите штрихкод еще раз"
        )
    await state.update_data(barcode=text)
    await state.set_state(GenerateBarcode.price)
    await message.answer("Напишите цену товара", reply_markup=ReplyKeyboardRemove())


async def photo_barcode(
    message: Message, state: FSMContext, bot: Bot, log_e: LoggerEGAIS
):
    chat_id = message.chat.id
    barcode_path = os.path.join(config.dir_path, "files", "boxnumbers", str(chat_id))
    img = await bot.get_file(message.photo[-1].file_id)
    if not os.path.exists(barcode_path):
        os.mkdir(barcode_path)
    file = os.path.join(barcode_path, f"barcode_{message.message_id}.jpg")
    await bot.download_file(img.file_path, file)

    barcodes_from_img = await read_barcodes_from_image(file)
    log_e.info(f'Отсканировал фото "{barcodes_from_img}"')

    if len(barcodes_from_img) == 0:  # Если не нашлись штрихкода на картинке
        await check_file_exist(
            file,
            "На данном фото <b><u>не найдено</u></b> штрихкодов",
            bot,
            message,
            log_e,
        )
        return
    elif len(barcodes_from_img) > 1:
        await check_file_exist(
            file,
            "На данном фото найдено <b><u>несколько</u></b> штрихкодов",
            bot,
            message,
            log_e,
        )
        return

    if os.path.exists(file):
        await asyncio.sleep(0.20)
        os.remove(file)

    await state.update_data(barcode=barcodes_from_img[0].strip())
    await state.set_state(GenerateBarcode.price)
    await message.answer("Напишите цену товара", reply_markup=ReplyKeyboardRemove())


async def document_barcode(
    message: Message, state: FSMContext, bot: Bot, log_e: LoggerEGAIS
):
    chat_id = message.chat.id
    barcode_path = os.path.join(config.dir_path, "files", "boxnumbers", str(chat_id))
    img = await bot.get_file(message.document.file_id)
    if not os.path.exists(barcode_path):
        os.mkdir(barcode_path)
    file = os.path.join(barcode_path, f"barcode_{message.message_id}.jpg")
    await bot.download_file(img.file_path, file)

    barcodes_from_img = await read_barcodes_from_image(file)
    log_e.info(f'Отсканировал фото "{barcodes_from_img}"')

    if len(barcodes_from_img) == 0:  # Если не нашлись штрихкода на картинке
        await check_file_exist(
            file,
            "На данном фото <b><u>не найдено</u></b> штрихкодов\nПришлите новое фото или напишите цифры штрихкода",
            bot,
            message,
            log_e,
        )
        return
    elif len(barcodes_from_img) > 1:
        await check_file_exist(
            file,
            "На данном фото найдено <b><u>несколько</u></b> штрихкодов\nПришлите новое фото или напишите цифры штрихкода",
            bot,
            message,
            log_e,
        )
        return

    if os.path.exists(file):
        await asyncio.sleep(0.20)
        os.remove(file)

    await state.update_data(barcode=barcodes_from_img[0].strip())
    await state.set_state(GenerateBarcode.price)
    await message.answer("Напишите цену товара", reply_markup=ReplyKeyboardRemove())


async def price(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    price = message.text
    if re.findall(",", message.text):
        price = price.replace(",", ".")

    check_price = price.replace(".", "")
    if not check_price.isdecimal():
        log_e.error(f'Цена не только из цифр "{price}"')
        await message.answer(texts.error_price_not_decimal)
        return
    log_e.info(f'Ввели цену товаров "{price}"')
    await state.update_data(price=price)
    await state.set_state(GenerateBarcode.name)
    await message.answer("Напишите название товара")


async def accept_name(
    message: Message, state: FSMContext, bot: Bot, log_e: LoggerEGAIS
):
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    op_mode, measure, dcode, tmctype, price = (
        data["op_mode"],
        data["measure"],
        data["dcode"],
        data["tmctype"],
        data["price"],
    )
    if message.text is None:
        log_e.debug(message.model_dump_json())
        log_e.error("Напишите ответным сообщением <b>название</b> товара")
        await message.answer(
            texts.error_head + "Напишите ответным сообщением <b>название</b> товара"
        )
        return
    names = message.text.split("\n")
    log_e.info(f'Ввели название товаров "{names}"')
    for name in names:
        await generate_barcode(
            cash_number=f"cash-{cash.shopcode}-{cash.cashcode}",
            name=name,
            op_mode=op_mode,
            measure=measure,
            dcode=dcode,
            bcode=data.get("barcode"),
            tmctype=tmctype,
            price=price,
            qdefault=data.get("qdefault", 1),
        )
    path = generate_pdf(f"cash-{cash.shopcode}-{cash.cashcode}")
    await bot.send_document(message.chat.id, document=FSInputFile(path))
    try:
        await add_barcodes_in_cash(
            cash.ip(),
            await get_barcodes_for_add(f"cash-{cash.shopcode}-{cash.cashcode}"),
        )
        if not config.develope_mode:
            await create_goods_log(
                cash_number=cash.shopcode,
                level="SUCCESS",
                type="Сгенерировали",
                inn=data.get("inn"),
                price=price,
                otdel=dcode,
                op_mode=op_mode,
                user_id=message.chat.id,
            )
        log_e.success(f"Успешно сгенерирован {len(names)} штриход(-а)")
        if len(names) == 1:
            await message.answer(
                "Успешно создан 1 штрихкод, в течении 5 минут (обычно мгновенно) он будет загружен на кассу"
            )
        else:
            await message.answer(
                f"Успешно создано {len(names)} штрихкода(-ов), через 5 минут они будут загружены на кассу"
            )
        # await state.clear()
        # await state.update_data(foreman_cash=cash.model_dump_json(by_alias=True))
    except sqlalchemy.exc.OperationalError as ex:
        log_e.exception(ex)
        text = (
            "К сожалению, в данный момент нет соединения с кассой.\n"
            "Пожалуйста, проверьте ваше интернет-соединение.\n"
            "Штрихкоды будут загружены автоматически, через 5 минут после восстановления связи\n"
        )
        msg = await texts.error_message_wp(cash, text)
        await message.answer(texts.error_head + text, reply_markup=kb_whatsapp_url(msg))
