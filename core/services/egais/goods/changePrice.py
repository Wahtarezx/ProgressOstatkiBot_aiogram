import asyncio
import os
import re

import sqlalchemy
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove

import config
from core.database.query_BOT import create_barcode, create_goods_log
from core.services.egais.TTN.accept import read_barcodes_from_image, check_file_exist
from core.keyboards.inline import kb_whatsapp_url
from core.keyboards.reply import one_time_scanner
from core.loggers.egais_logger import LoggerEGAIS
from core.services.egais.goods.create_barcodes import regex_check_barcode
from core.services.egais.logins.pd_models import Cash
from core.services.markirovka.keyboard.inline import kb_again_price
from core.services.markirovka.trueapi import get_ean_from_gtin
from core.utils import texts
from core.utils.foreman.pd_model import ForemanCash
from core.utils.states import ChangePrice
from core.cron.barcodes import update_price_in_cash


async def send_barcode(call: CallbackQuery, bot: Bot, state: FSMContext):
    await state.set_state(ChangePrice.barcode)
    await bot.send_message(
        call.message.chat.id, texts.scan_photo_or_text, reply_markup=one_time_scanner()
    )
    await call.answer()


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

    regex_barcode = regex_check_barcode(get_ean_from_gtin(text))
    if regex_barcode is not None:
        text = regex_barcode
        log_e.debug("Подошел под регулярное выражение")
    elif text.isdigit():
        log_e.debug("Состоит только из цифр")
    elif "*" in text:
        log_e.debug("Есть * в штрихкоде")
    else:
        log_e.error("Отсканируйте штрихкод или маркировку у товара.")
        await message.answer(
            texts.error_head + "Отсканируйте штрихкод или маркировку у товара."
        )
        return

    await state.update_data(barcode=text)
    await state.set_state(ChangePrice.price)
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

    barcode = barcodes_from_img[0].strip()
    regex_barcode = regex_check_barcode(get_ean_from_gtin(barcode))
    if regex_barcode is not None:
        barcode = regex_barcode
        log_e.debug("Подошел под регулярное выражение")
    elif barcode.isdigit():
        log_e.debug("Состоит только из цифр")
    else:
        log_e.error("Отсканируйте штрихкод или маркировку у товара.")
        await message.answer(
            texts.error_head + "Отсканируйте штрихкод или маркировку у товара."
        )
        return

    await state.update_data(barcode=barcode)
    await state.set_state(ChangePrice.price)
    await message.answer("Напишите цену товара")


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

    barcode = barcodes_from_img[0].strip()
    regex_barcode = regex_check_barcode(get_ean_from_gtin(barcode))
    if regex_barcode is not None:
        barcode = regex_barcode
        log_e.debug("Подошел под регулярное выражение")
    elif barcode.isdigit():
        log_e.debug("Состоит только из цифр")
    else:
        log_e.error("Отсканируйте штрихкод или маркировку у товара.")
        await message.answer(
            texts.error_head + "Отсканируйте штрихкод или маркировку у товара."
        )
        return

    await state.update_data(barcode=barcode)
    await state.set_state(ChangePrice.price)
    await message.answer("Напишите цену товара")


async def final(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    price = message.text
    if re.findall(",", message.text):
        price = price.replace(",", ".")

    check_price = price.replace(".", "")
    if not check_price.isdecimal():
        log_e.error(f'Цена не только из цифр "{price}"')
        await message.answer(texts.error_price_not_decimal)
        return
    log_e.info(f'Ввели цену товаров "{price}"')
    await state.set_state(ChangePrice.final)
    data = await state.get_data()
    fcash = ForemanCash.model_validate_json(data["foreman_cash"])
    try:
        await create_barcode(
            bcode=data["barcode"],
            cash_number=f"cash-{fcash.shopcode}-{fcash.cashcode}",
            price=price,
            status="setprice",
        )
        await update_price_in_cash(
            fcash.ip(), f"cash-{fcash.shopcode}-{fcash.cashcode}"
        )
        log_e.success(f'Изменили цену штрихкода "{data["barcode"]}" на "{price}"')
        await create_goods_log(
            cash_number=fcash.shopcode,
            level="SUCCESS",
            type="Изменили цену",
            inn=fcash.inn,
            bcode=data["barcode"],
            price=price,
            user_id=message.chat.id,
        )
        await message.answer(
            f'Изменили цену штрихкода "{data["barcode"]}" на "{price}"'
        )
        await message.answer(
            "Вы снова хотите исправить цену?", reply_markup=kb_again_price()
        )
    except sqlalchemy.exc.OperationalError as ex:
        log_e.error("Касса не в сети")
        log_e.exception(ex)
        text = (
            "К сожалению, в данный момент нет соединения с кассой. "
            "Штрихкоды не могут быть загружены. "
            "Пожалуйста, проверьте ваше интернет-соединение. "
            "Штрихкоды будут загружены автоматически через 5 минут после восстановления связи"
        )
        msg = await texts.error_message_wp(fcash, text)
        await message.answer(texts.error_head + text, reply_markup=kb_whatsapp_url(msg))
