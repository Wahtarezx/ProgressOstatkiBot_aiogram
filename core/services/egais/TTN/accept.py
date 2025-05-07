import asyncio
import os
import re
from pprint import pprint
from typing import List

import cv2
import httpx
import pytesseract
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.types import ReplyKeyboardRemove
from aiogram_media_group import media_group_handler
from pyzbar import pyzbar

from core.database.query_BOT import create_ttn_log
from core.database.query_logs import DBLogs
from core.keyboards.inline import *
from core.keyboards.reply import scanner
from core.loggers.egais_logger import LoggerEGAIS
from core.loggers.make_loggers import except_log
from core.services.egais.TTN.pd_model import Waybills
from core.utils import texts
from core.utils.UTM import UTM
from core.utils.callbackdata import AcceptTTN, SendAcceptTTN
from core.utils.check_sub_tg_channel import check_tg_channel_sub, wait_to_subscribe
from core.utils.states import StateTTNs

lock = asyncio.Lock()
db = Database()


async def accept_all_ttns(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    wb = Waybills.model_validate_json(data.get("wb"))
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    log_e.button("Подтвердить все накладные")
    await call.message.edit_text(texts.load_information)
    utm = UTM(ip=cash.ip(), port=wb.port)
    WB_ttns = await utm.get_Waybill_and_FORM2REGINFO()
    log_e.info(f'Найдено накладных "{len(WB_ttns)}"')
    await call.message.answer(f"Найдено накладных: <b><u>{len(WB_ttns)}</u></b>")
    for count, ttn in enumerate(WB_ttns, 1):
        ttn_egais = ttn.ttn_egais.split("-")[1]
        response = await utm.send_WayBillv4(ttn_egais)
        if response.status_code == 200:
            url = f"http://{cash.ip()}:{wb.port}/opt/out"
            url_f2r = f"{url}/FORM2REGINFO/{ttn.id_f2r}"
            url_wb = f"{url}/WayBill_v4/{ttn.id_wb}"
            await utm.add_to_whitelist(
                url_wb,
                await utm.get_box_info_from_Waybill(url_wb, True),
                f"cash-{cash.shopcode}-{cash.cashcode}",
            )
            await utm._delete(url_f2r)
            await utm._delete(url_wb)
            log_e.success(f'Приняли накладную "{ttn_egais}"')
            await create_ttn_log(
                cash_number=cash.shopcode,
                user_id=call.message.chat.id,
                level="SUCCES",
                type="Подтвердить",
                inn=wb.inn,
                shipper_inn=ttn.shipper_inn,
                ttns_egais=ttn_egais,
                description="Автоматически принять всё",
            )
            text = (
                "✅Акт потдверждения накладной успешно отправлен. "
                "Накладная будет принята в течении 5 минут\n"
                ""
            )
            text += f"Поставщик: <code>{ttn.shipper_name}</code>\n"
            text += f"Номер накладной: <code>{ttn.wbnumber}</code>\n"
            text += (
                f"Дата: <code>{ttn.date}</code>\n"
                f"ТТН-ЕГАИС: <code>{ttn.ttn_egais}</code>\n"
            )
            await call.message.answer(text)


async def read_barcodes_from_image(image_path):
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    barcodes = pyzbar.decode(image)
    barcode_data_list = []
    for barcode in barcodes:
        barcode_data = barcode.data.decode("utf-8")
        barcode_data_list.append(barcode_data)
    return barcode_data_list


async def read_numbers_from_image(image_path):
    if os.name == "posix":
        pytesseract.pytesseract.tesseract_cmd = r"/usr/local/bin/tesseract"
        pytesseract.pytesseract.TESSDATA_PREFIX = (
            r"/usr/share/tesseract-ocr/4.00/tessdata"
        )
        custom_configs = [
            r"-l rus --psm 3 --oem 2",
            r"-l rus --psm 1 --oem 2",
            r"-l rus --psm 6 --oem 2",
            r"-l rus --psm 11 --oem 2",
        ]
    else:
        pytesseract.pytesseract.tesseract_cmd = (
            r"C:\Users\User\AppData\Local\Tesseract-OCR\tesseract.exe"
        )
        custom_configs = [
            r"--psm 3 --oem 2",
            r"--psm 1 --oem 2",
            r"--psm 6 --oem 2",
            r"--psm 11 --oem 2",
        ]

    image = cv2.imread(str(image_path))
    result = []

    for custom_config in custom_configs:
        try:
            decode_barcode = re.findall(
                r"\b\d{8}(?:\d{3})?(?:\d{15})?\b",
                pytesseract.image_to_string(image, config=custom_config),
            )
            for db in decode_barcode:
                if not re.findall(db, ",".join(result)):
                    result.append(db)
        except FileNotFoundError:
            continue
    return result


async def find_amark_or_box_by_numbers(
        numbers: list,
        log_e: LoggerEGAIS,
        result,
        bot,
        message,
        barcodes: list,
        boxs: list,
        file=None,
):
    for bcode in numbers:
        match = 0
        if (
                re.findall("^[0-9]{8}$", bcode)
                or re.findall("^[0-9]{11}$", bcode)
                or re.findall("^[0-9]{6}$", bcode)
                or re.findall("^[A-Z0-9]{150}$", bcode)
                or re.findall("^[A-Z0-9]{68}$", bcode)
        ):
            if re.findall("^[0-9]{11}$", bcode):
                bcode = bcode[3:]
            for pos in result:
                for mark in pos.amarks:
                    if re.findall(bcode, mark):
                        match += 1
                        log_e.debug(f'Данная акцизка "{bcode}" уже принята')
                        text = f'Данная акцизная марка "<code>{bcode}</code>" уже принята. Отправьте акцизную марку от другой позиции'
                        if file:
                            await check_file_exist(file, text, bot, message, log_e)
                        else:
                            await bot.send_message(
                                message.chat.id, texts.error_head + text
                            )
                        break
            if match == 0:
                for mark_in_ttn in (mark for box in boxs for mark in box.amarks):
                    if re.findall(bcode, mark_in_ttn):
                        match += 1
                        break
                if match == 0:
                    text = f"Данной марки <code>{bcode}</code> не найдено в накладной"
                    if file:
                        await check_file_exist(file, text, bot, message, log_e)
                    else:
                        await bot.send_message(message.chat.id, texts.error_head + text)
                else:
                    barcodes.append(bcode)

        elif re.findall("^[0-9]{26}$", bcode):
            if bcode not in (b.boxnumber for b in boxs):
                text = (
                        texts.error_head
                        + f'Данной коробки <code>"{bcode}"</code> не найдено в накладной'
                )
                await bot.send_message(message.chat.id, text)
                log_e.debug(f'Данной коробки "{bcode}" не найдено в накладной')
            elif bcode in (b.boxnumber for b in result):
                text = (
                        texts.error_head
                        + f'Вы уже отправляли данную коробку\n"<code>{str(bcode).strip()}</code>"'
                )
                await bot.send_message(message.chat.id, text)
                log_e.debug(f'Вы уже отправляли данную коробку "{bcode}"')
            else:
                log_e.debug(f'Нашел коробку по цифрам "{bcode}"')
                barcodes.append(bcode)
        else:
            text = f'Данная позиция "<code>{bcode}</code>" не коробка, и не акцизная марка. Попробуйте снова'
            await bot.send_message(message.chat.id, texts.error_head + text)
    return barcodes


async def accept_ttn_by_amark_or_box(
        boxs: list, barcodes: list, log_e: LoggerEGAIS, result: list, new_boxs
):
    for box in boxs:
        match = 0
        if any(
                [b.scaned for b in boxs if b.boxnumber == box.boxnumber]
        ) and box.identity not in (b.identity for b in result):
            result.append(
                new_boxs(
                    box.identity,
                    box.name,
                    box.capacity,
                    box.boxnumber,
                    box.count_bottles,
                    box.amarks,
                    True,
                )
            )
            continue
        for barcode in barcodes:
            if (
                    re.findall("^[0-9]{8}$", barcode)
                    or re.findall("^[A-Z0-9]{150}$", barcode)
                    or re.findall("^[A-Z0-9]{68}$", barcode)
            ):
                for amark in box.amarks:
                    if re.findall(barcode, amark):
                        match += 1
                        log_e.info(f"Принял акцизу {barcode}")
                        result.append(
                            new_boxs(
                                box.identity,
                                box.name,
                                box.capacity,
                                box.boxnumber,
                                box.count_bottles,
                                box.amarks,
                                True,
                            )
                        )
            elif barcode == box.boxnumber:
                match += 1
                log_e.info(f"Принял коробку {barcode}")
                result.append(
                    new_boxs(
                        box.identity,
                        box.name,
                        box.capacity,
                        box.boxnumber,
                        box.count_bottles,
                        box.amarks,
                        True,
                    )
                )
        if match == 0:
            if box.boxnumber not in (b.boxnumber for b in result):
                result.append(
                    new_boxs(
                        box.identity,
                        box.name,
                        box.capacity,
                        box.boxnumber,
                        box.count_bottles,
                        box.amarks,
                        False,
                    )
                )
            else:
                if box.identity not in (b.identity for b in result):
                    result.append(
                        new_boxs(
                            box.identity,
                            box.name,
                            box.capacity,
                            box.boxnumber,
                            box.count_bottles,
                            box.amarks,
                            False,
                        )
                    )
    return result


async def menu_back_ttns(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Назад")
    await call.message.answer(texts.WayBills, reply_markup=kb_menu_ttns())
    await call.answer()


async def choose_accept_ttns(
        call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    db_logs = DBLogs()
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    # Проверка на подписку тг канала
    if await db_logs.count_accept_ttns(cash.shopcode) > 5:
        if not await check_tg_channel_sub(call.message.bot, call.from_user.id):
            await call.message.edit_text(
                texts.sub_to_tg_channel, reply_markup=kb_sub_to_channel()
            )
            if await wait_to_subscribe(call) is None:
                log_e.error("Истекло время ожидания подписки на канал")
                await call.message.edit_text(
                    texts.fail_to_wait_sub,
                    reply_markup=kb_fail_sub("Подтвердить накладные", call.data),
                )
                return
        else:
            log_e.info("Подписка на тг канал есть")
    if not config.develope_mode:
        await call.message.edit_text("Загрузка накладных...")
    log_e.button("Приём ТТН")
    wb = Waybills.model_validate_json(data.get("wb"))
    client = await db.get_client_info(call.message.chat.id)
    utm = UTM(ip=cash.ip(), port=wb.port)
    ttns = await utm.get_Waybill_and_FORM2REGINFO()
    if not ttns:
        log_e.error("Не найдено накладных для подтверждения")
        await call.message.delete()
        msg = (
            "Не найдено накладных для подтверждения\n"
            "Пожалуйста попробуйте перевыслать накладную или можете обратиться в тех.поддержку"
        )
        await call.message.answer(
            texts.error_head + msg,
            reply_markup=kb_whatsapp_url(await texts.error_message_wp(cash, msg)),
        )
        await call.message.answer(texts.WayBills, reply_markup=kb_menu_ttns())
        return
    await call.message.edit_text(
        "Выберите накладную",
        reply_markup=await kb_choose_ttn(
            TTNs=ttns,
            cash=cash,
            client=client,
        ),
    )


async def start_accept_ttns(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: AcceptTTN,
        bot: Bot,
        log_e: LoggerEGAIS,
):
    await call.message.edit_text("Загрузка накладной...")
    data = await state.get_data()
    log_e.info(f'Выбрали накладную "{callback_data.ttn}"')
    wb = Waybills.model_validate_json(data.get("wb"))
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    id_f2r = callback_data.id_f2r
    id_wb = callback_data.id_wb
    ttn_egais = callback_data.ttn.split("-")[1]
    url_utm = f"http://{cash.ip()}:{wb.port}/opt/out"
    url_f2r, url_wb = f"{url_utm}/{id_f2r}", f"{url_utm}/{id_wb}"
    utm = UTM(ip=cash.ip(), port=wb.port)
    beer_ttn = await utm.check_beer_waybill(url_wb, wb.port)
    old_msg_to_delete = []
    if beer_ttn:
        log_e.debug("Пивная накладная")
        await state.update_data(
            ttn_egais=ttn_egais,
            id_f2r=id_f2r,
            id_wb=id_wb,
            busy=False,
            alco_ttn=False,
            shipper_inn=callback_data.inn,
        )
        msg_to_delete = await call.message.edit_text(
            texts.beer_accept_text(beer_ttn),
            reply_markup=kb_accept_beer_ttn(await state.get_data()),
        )
        old_msg_to_delete.append(msg_to_delete.message_id)
    else:
        log_e.debug("Алкогольная накладная")
        if not os.path.exists(os.path.join(config.dir_path, "files", "boxnumbers")):
            os.makedirs(os.path.join(config.dir_path, "files", "boxnumbers"))
        boxs = await utm.get_box_info_from_Waybill(url_wb)
        await state.update_data(
            ttn_egais=ttn_egais,
            boxs=boxs,
            id_f2r=id_f2r,
            id_wb=id_wb,
            alco_ttn=True,
            shipper_inn=callback_data.inn,
        )
        await call.message.delete()
        text = (
            "➖➖➖➖ℹ️<b><u>Инструкция</u></b>ℹ️➖➖➖➖\n"
            "Для приема ТТН отправьте фото штрих-кодов с коробок, либо ввидите штрих-код текстом. Можно отправлять по одному, либо сразу несколько фото.\n"
            "Пример фото:"
        )
        await bot.send_photo(
            call.message.chat.id,
            FSInputFile(os.path.join(config.dir_path, "files", "startAccept.jpg")),
            caption=text,
            reply_markup=scanner(),
        )
        messages = texts.accept_text(boxs)
        for count, message in enumerate(messages, start=1):
            if count != len(messages):
                msg_to_delete = await call.message.answer(message)
            else:
                msg_to_delete = await call.message.answer(
                    message, reply_markup=await kb_accept_ttn(await state.get_data())
                )
            old_msg_to_delete.append(msg_to_delete.message_id)
        log_e.info(str(await state.get_data()))
        await state.set_state(StateTTNs.accept_ttn)
        await state.update_data(
            old_msg_to_delete=old_msg_to_delete,
        )


async def check_file_exist(file, msg, bot: Bot, message: Message, log_e: LoggerEGAIS):
    if os.path.exists(file):
        await bot.send_photo(message.chat.id, photo=FSInputFile(file), caption=msg)
        log_e.debug(msg)
        await asyncio.sleep(0.20)
        os.remove(file)


async def wait_busy(state: FSMContext):
    data = await state.get_data()
    if data.get("busy"):
        while True:
            await asyncio.sleep(0.05)
            data = await state.get_data()
            if not data.get("busy"):
                break
    await state.update_data(busy=True)


async def get_boxs(boxs):
    """
    :param boxs: Коробки
    :return: [namedtuple('Box', 'name capacity boxnumber count_bottles amarks scaned'), ...]
    """
    boxinfo = namedtuple(
        "Box", "identity name capacity boxnumber count_bottles amarks scaned"
    )
    result = []
    for identity, name, capacity, boxnumber, count_bottles, amarks, scaned in boxs:
        result.append(
            boxinfo(identity, name, capacity, boxnumber, count_bottles, amarks, scaned)
        )
    return result


async def message_accept_ttns(
        message: Message, state: FSMContext, bot: Bot, log_e: LoggerEGAIS
):
    async with lock:
        data = await state.get_data()
        if message.web_app_data is not None:

            def clean_and_decode(value):
                cleaned_value = value.replace("\x1d", "")
                if "\\u" in cleaned_value:
                    decoded_value = cleaned_value.encode("utf-8").decode(
                        "unicode_escape"
                    )
                else:
                    decoded_value = cleaned_value
                return decoded_value

            messages = [
                clean_and_decode(item) for item in json.loads(message.web_app_data.data)
            ]
            log_e.info(f'Отсканировал сканером штрихкод "{messages}"')
        else:
            messages = message.text.split()
            log_e.info(f'Написали штрихкод(-а) "{messages}"')
        boxs = await get_boxs(data.get("boxs"))
        result = [box for box in boxs if box.scaned]
        new_boxs = namedtuple(
            "Box", "identity name capacity boxnumber count_bottles amarks scaned"
        )

        barcodes = []
        finded = await find_amark_or_box_by_numbers(
            messages, log_e, result, bot, message, barcodes, boxs
        )
        barcodes = finded

        # Если ничего не нашел
        if len(barcodes) == 0:
            await state.update_data(busy=False)
            return

        result = await accept_ttn_by_amark_or_box(
            boxs, barcodes, log_e, result, new_boxs
        )

        await state.update_data(busy=False, boxs=result)
        box_scaned = [box for box in result if box.scaned]
        log_e.info(f"Принято {len(box_scaned)}/{len(result)}")
        messages = texts.accept_text(result)
        old_msg_to_delete: list = data.get("old_msg_to_delete", [])
        for count, msg in enumerate(messages, start=1):
            if count != len(messages):
                msg_to_delete = await message.answer(msg)
            else:
                msg_to_delete = await message.answer(
                    msg, reply_markup=await kb_accept_ttn(await state.get_data())
                )
            old_msg_to_delete.append(msg_to_delete.message_id)
        await state.update_data(old_msg_to_delete=old_msg_to_delete)


@media_group_handler
async def mediagroup_accept_ttns(
        messages: List[Message], state: FSMContext, bot: Bot, log_e: LoggerEGAIS
):
    async with lock:
        data = await state.get_data()
        chat_id = messages[0].chat.id
        boxs = await get_boxs(data.get("boxs"))
        barcodes = []
        result = [box for box in boxs if box.scaned]
        barcode_path = os.path.join(
            config.dir_path, "files", "boxnumbers", str(chat_id)
        )

        for message in messages:
            file = await bot.get_file(message.photo[-1].file_id)

            if not os.path.exists(barcode_path):
                os.mkdir(barcode_path)

            file_path = os.path.join(barcode_path, f"barcode_{message.message_id}.jpg")
            await bot.download_file(file.file_path, file_path)
        for file in os.listdir(barcode_path):
            file = os.path.join(barcode_path, file)
            try:
                barcodes_from_img = await read_barcodes_from_image(file)
                log_e.info(f'Отсканировал фото на коробки "{barcodes_from_img}"')

                if len(barcodes_from_img) > 0:
                    barcodes += await find_amark_or_box_by_numbers(
                        barcodes_from_img,
                        log_e,
                        result,
                        bot,
                        message,
                        barcodes,
                        boxs,
                        file,
                    )
                else:
                    number_from_img = await read_numbers_from_image(file)
                    log_e.info(f'Отсканировал цифры на фото "{number_from_img}"')
                    if len(number_from_img) > 0:
                        barcodes += await find_amark_or_box_by_numbers(
                            number_from_img,
                            log_e,
                            result,
                            bot,
                            message,
                            barcodes,
                            boxs,
                            file,
                        )
                    else:
                        await check_file_exist(
                            file,
                            "На данном фото <b><u>не найдено</u></b> штрихкода коробки или акцизной марки",
                            bot,
                            messages[0],
                            log_e,
                        )

                if os.path.exists(file):
                    await asyncio.sleep(0.20)
                    os.remove(file)

            except TypeError as e:
                log_e.exception(f"TypeError: {e}")
            except FileNotFoundError:
                log_e.debug(f'Файл не найден "{file}"')
            except PermissionError:
                log_e.debug(f'Файл занят другим процессом "{file}"')

        # Если ничего не нашел
        if len(barcodes) == 0:
            await state.update_data(busy=False)
            return

        barcodes = list(set(barcodes))
        log_e.debug(f'Нашел коробки "{barcodes}"')
        new_boxs = namedtuple(
            "Box", "identity name capacity boxnumber count_bottles amarks scaned"
        )

        result = await accept_ttn_by_amark_or_box(
            boxs, barcodes, log_e, result, new_boxs
        )

        await state.update_data(busy=False, boxs=result)
        box_scaned = [box for box in result if box.scaned]
        log_e.info(f"Принято {len(box_scaned)}/{len(result)}")
        messages = texts.accept_text(result)
        old_msg_to_delete: list = data.get("old_msg_to_delete", [])
        for count, msg in enumerate(messages, start=1):
            if count != len(messages):
                msg_to_delete = await message.answer(msg)
            else:
                msg_to_delete = await message.answer(
                    msg, reply_markup=await kb_accept_ttn(await state.get_data())
                )
            old_msg_to_delete.append(msg_to_delete.message_id)
        await state.update_data(old_msg_to_delete=old_msg_to_delete)


async def photo_accept_ttns(
        message: Message, state: FSMContext, bot: Bot, log_e: LoggerEGAIS
):
    async with lock:

        chat_id = message.chat.id
        data = await state.get_data()

        # Коробки
        boxs = await get_boxs(data.get("boxs"))
        result = [box for box in boxs if box.scaned]
        barcodes = []

        # Качаем фотку и сохраняем в папку, название папки = айди чата
        barcode_path = os.path.join(
            config.dir_path, "files", "boxnumbers", str(chat_id)
        )
        img = await bot.get_file(message.photo[-1].file_id)
        if not os.path.exists(barcode_path):
            os.mkdir(barcode_path)
        file = os.path.join(barcode_path, f"barcode_{message.message_id}.jpg")
        await bot.download_file(img.file_path, file)

        try:
            barcodes_from_img = await read_barcodes_from_image(file)
            log_e.info(f'Отсканировал фото "{barcodes_from_img}"')

            if len(barcodes_from_img) > 0:
                barcodes = await find_amark_or_box_by_numbers(
                    barcodes_from_img, log_e, result, bot, message, barcodes, boxs, file
                )
            else:
                number_from_img = await read_numbers_from_image(file)
                log_e.info(f'Отсканировал цифры на фото "{number_from_img}"')
                if len(number_from_img) > 0:
                    barcodes = await find_amark_or_box_by_numbers(
                        number_from_img, log_e, result, bot, message, barcodes, boxs
                    )
                else:
                    await check_file_exist(
                        file,
                        "На данном фото <b><u>не найдено</u></b> штрихкода коробки или акцизной марки",
                        bot,
                        message,
                        log_e,
                    )

            if os.path.exists(file):
                await asyncio.sleep(0.20)
                os.remove(file)
        except TypeError:
            log_e.debug(f"TypeError: {file}")
        except FileNotFoundError:
            log_e.debug(f'Файл не найден "{file}"')
        except PermissionError:
            log_e.debug(f'Файл занят другим процессом "{file}"')

        if len(barcodes) == 0:
            await state.update_data(busy=False)
            return
        barcodes = list(set(barcodes))
        log_e.debug(f'Нашел коробки "{barcodes}"')
        new_boxs = namedtuple(
            "Box", "identity name capacity boxnumber count_bottles amarks scaned"
        )

        result = await accept_ttn_by_amark_or_box(
            boxs, barcodes, log_e, result, new_boxs
        )

        await state.update_data(busy=False, boxs=result)
        box_scaned = [box for box in result if box.scaned]
        log_e.info(f"Принято {len(box_scaned)}/{len(result)}")
        messages = texts.accept_text(result)
        old_msg_to_delete: list = data.get("old_msg_to_delete", [])
        for count, msg in enumerate(messages, start=1):
            if count != len(messages):
                msg_to_delete = await message.answer(msg)
            else:
                msg_to_delete = await message.answer(
                    msg, reply_markup=await kb_accept_ttn(await state.get_data())
                )
            old_msg_to_delete.append(msg_to_delete.message_id)
        await state.update_data(old_msg_to_delete=old_msg_to_delete)


async def document_accept_ttn(
        message: Message, state: FSMContext, bot: Bot, log_e: LoggerEGAIS
):
    async with lock:
        pprint(message)
        data = await state.get_data()

        chat_id = message.chat.id

        # Коробки
        boxs = await get_boxs(data.get("boxs"))
        result = [box for box in boxs if box.scaned]
        barcodes = []

        # Качаем фотку и сохраняем в папку, название папки = айди чата
        barcode_path = os.path.join(
            config.dir_path, "files", "boxnumbers", str(chat_id)
        )
        img = await bot.get_file(message.document.file_id)
        if not os.path.exists(barcode_path):
            os.mkdir(barcode_path)
        file = os.path.join(barcode_path, f"barcode_{message.message_id}.jpg")
        await bot.download_file(img.file_path, file)
        try:
            barcodes_from_img = await read_barcodes_from_image(file)
            log_e.info(f'Отсканировал фото "{barcodes_from_img}"')

            if len(barcodes_from_img) > 0:
                barcodes = await find_amark_or_box_by_numbers(
                    barcodes_from_img, log_e, result, bot, message, barcodes, boxs, file
                )
            else:
                number_from_img = await read_numbers_from_image(file)
                log_e.info(f'Отсканировал цифры на фото "{number_from_img}"')
                if len(number_from_img) > 0:
                    barcodes = await find_amark_or_box_by_numbers(
                        number_from_img,
                        log_e,
                        result,
                        bot,
                        message,
                        barcodes,
                        boxs,
                        file,
                    )
                else:
                    await check_file_exist(
                        file,
                        "На данном фото <b><u>не найдено</u></b> штрихкода коробки или акцизной марки",
                        bot,
                        message,
                        log_e,
                    )

            if os.path.exists(file):
                await asyncio.sleep(0.20)
                os.remove(file)
        except TypeError:
            log_e.debug(f"TypeError: {file}")
        except FileNotFoundError:
            log_e.debug(f'Файл не найден "{file}"')
        except PermissionError:
            log_e.debug(f'Файл занят другим процессом "{file}"')

        if len(barcodes) == 0:
            await state.update_data(busy=False)
            return
        barcodes = list(set(barcodes))
        log_e.debug(f'Нашел коробки "{barcodes}"')
        new_boxs = namedtuple(
            "Box", "identity name capacity boxnumber count_bottles amarks scaned"
        )

        result = await accept_ttn_by_amark_or_box(
            boxs, barcodes, log_e, result, new_boxs
        )

        await state.update_data(busy=False, boxs=result)
        box_scaned = [box for box in result if box.scaned]
        log_e.info(f"Принято {len(box_scaned)}/{len(result)}")
        messages = texts.accept_text(result)
        old_msg_to_delete: list = data.get("old_msg_to_delete", [])
        for count, msg in enumerate(messages, start=1):
            if count != len(messages):
                msg_to_delete = await message.answer(msg)
            else:
                msg_to_delete = await message.answer(
                    msg, reply_markup=await kb_accept_ttn(await state.get_data())
                )
            old_msg_to_delete.append(msg_to_delete.message_id)
        await state.update_data(old_msg_to_delete=old_msg_to_delete)


async def send_accept_ttn(
        call: CallbackQuery,
        bot: Bot,
        state: FSMContext,
        callback_data: SendAcceptTTN,
        log_e: LoggerEGAIS,
):
    log_e.button("Принять накладную")
    await call.message.edit_text(
        "Идёт процесс потдверждения накладной. Загрузка займет не дольше 1-ой минуты"
    )
    data = await state.get_data()
    wb = Waybills.model_validate_json(data.get("wb"))
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    url = f"http://{cash.ip()}:{wb.port}/opt/out"
    url_f2r = f'{url}/FORM2REGINFO/{data.get("id_f2r")}'
    url_wb = f'{url}/WayBill_v4/{data.get("id_wb")}'
    utm = UTM(ip=cash.ip(), port=wb.port)

    response = await utm.send_WayBillv4(callback_data.ttn)
    log_e.info(f"response = {response.status_code}")
    if response.status_code == 200:
        if data.get("alco_ttn"):
            boxs = await get_boxs(data.get("boxs"))
            await utm.add_to_whitelist(url_wb, boxs, cash.shopcode)
        async with httpx.AsyncClient() as client:
            await client.delete(url_f2r, timeout=30.0)
            await client.delete(url_wb, timeout=30.0)
        log_e.success(f'Приняли накладную "{callback_data.ttn}"')
        if callback_data.auto:
            description = "Приняли накладную не сканируя"
        else:
            description = "Обычно"
        if not callback_data.alco:
            description = "Приняли пиво"
        await create_ttn_log(
            cash_number=cash.shopcode,
            user_id=call.message.chat.id,
            level="SUCCES",
            type="Подтвердить",
            inn=wb.inn,
            shipper_inn=data.get("shipper_inn"),
            ttns_egais=callback_data.ttn,
            description=description,
        )
        await bot.send_message(
            chat_id=call.message.chat.id,
            text="✅Акт потдверждения накладной успешно отправлен\n"
                 "Накладная будет принята в течении 5 минут",
            reply_markup=ReplyKeyboardRemove(),
        )
        old_msg_to_delete = data.get("old_msg_to_delete", [])
        for msg in old_msg_to_delete:
            try:
                await call.bot.delete_message(call.message.chat.id, msg)
            except Exception as e:
                except_log.exception(e)
            await asyncio.sleep(0.1)

    else:
        log_e.error(
            f'Накладная не принята "{callback_data.ttn}". Код ошибки "{response.status_code}"'
        )
        text = f'Попробуйте еще раз подтвердить накладную. Код ошибки "{response.status_code}"'
        await call.message.answer(
            texts.error_head + text,
            reply_markup=kb_whatsapp_url(
                message=await texts.error_message_wp(cash, text)
            ),
        )


async def choose_divirgence_ttn(
        call: CallbackQuery, state: FSMContext, bot: Bot, log_e: LoggerEGAIS
):
    await state.set_state(StateTTNs.choose_divirgence_ttn)
    data = await state.get_data()
    text = texts.divirgence_text(await get_boxs(data.get("boxs")))
    await call.message.edit_text(text)
    log_e.info("Вы уверены что хотите отправить акт расхождения?")
    text = (
        "Акт расхождения - это частичное подтвеждение накладной\n"
        "Вы уверены что хотите отправить акт расхождения?"
    )
    await bot.send_message(
        call.message.chat.id, text, reply_markup=kb_choose_divirgence_ttn()
    )


async def send_divirgence_ttn(
        call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    log_e.info("Отправили акт расхождения")
    await call.message.edit_text(
        "Идёт процесс отправки накладной. Загрузка займёт не дольше 1-ой минуты"
    )
    data = await state.get_data()
    wb = Waybills.model_validate_json(data.get("wb"))
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    url = f"http://{cash.ip()}:{wb.port}/opt/out"
    url_f2r = f'{url}/FORM2REGINFO/{data.get("id_f2r")}'
    url_wb = f'{url}/WayBill_v4/{data.get("id_wb")}'
    utm = UTM(ip=cash.ip(), port=wb.port)
    ttn_egais = data.get("ttn_egais")
    response = await utm.send_divirgence_ttn(
        url_wb, url_f2r, await get_boxs(data.get("boxs")), ttn_egais
    )
    if response.status_code == 200:
        await utm.add_to_whitelist(
            url_wb, await get_boxs(data.get("boxs")), cash.shopcode
        )
        async with httpx.AsyncClient() as client:
            await client.delete(url_f2r, timeout=30.0)
            await client.delete(url_wb, timeout=30.0)
        log_e.success(f'Акт расхождения успешно отправлен "{ttn_egais}"')
        await call.message.edit_text("✅Акт расхождения успешно отправлен\n")
        await create_ttn_log(
            cash_number=cash.shopcode,
            user_id=call.message.chat.id,
            level="SUCCES",
            type="Расхождение",
            inn=wb.inn,
            shipper_inn=data.get("shipper_inn"),
            ttns_egais=ttn_egais,
        )
    else:
        log_e.error(
            f'Накладная не принята "{ttn_egais}". Код ошибки "{response.status_code}"'
        )
        text = f'Попробуйте еще раз отправить акт расхождения. Код ошибки "{response.status_code}"'
        await call.message.answer(
            texts.error_head + text,
            reply_markup=kb_whatsapp_url(
                message=await texts.error_message_wp(cash, text)
            ),
        )


async def back_to_accept_ttn(
        call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    data = await state.get_data()
    boxs = await get_boxs(data.get("boxs"))
    log_e.button("Нет при отправке акта расхождения")
    messages = texts.accept_text(boxs)
    for count, msg in enumerate(messages, start=1):
        if count != len(messages):
            await call.message.answer(msg)
        else:
            await call.message.answer(
                msg, reply_markup=await kb_accept_ttn(await state.get_data())
            )

    await state.set_state(StateTTNs.accept_ttn)
