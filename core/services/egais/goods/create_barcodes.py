import asyncio
import datetime
import os
import re
from typing import Union

import cv2
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from pydantic import ValidationError
from pylibdmtx.pylibdmtx import decode
from sqlalchemy.exc import OperationalError

import config
from core.cron.barcodes import add_barcodes_in_cash
from core.database.artix.querys import ArtixCashDB
from core.database.query_BOT import (
    get_barcodes_for_add,
    create_goods_log,
    create_more_barcodes,
)
from core.keyboards import inline
from core.keyboards.inline import kb_addbcode_load_prepare_commit
from core.keyboards.reply import one_time_scanner
from core.loggers.egais_logger import LoggerEGAIS
from core.services.egais.TTN.accept import read_barcodes_from_image, check_file_exist
from core.services.egais.goods.pd_models import (
    Product,
    TmcType,
    _Goods,
    Dcode,
    TouchPanel,
    _Actionpanelitem,
    DraftBeerInfo,
    Measure,
    OpMode,
    UpdateHotkeyType,
)
from core.services.markirovka.callbackdata import (
    AddToTouchPanel,
    ActionpanelGoods,
    ActionPanelItem,
)
from core.services.markirovka.enums import GroupIds
from core.services.markirovka.trueapi import TrueApi, get_ean_from_gtin, ZnakAPIError
from core.utils import texts
from core.utils.callbackdata import SelectDcode, SelectMeasure, VolumeDraftBeer
from core.utils.foreman.pd_model import ForemanCash
from core.utils.states import AddToCashBarcode


def regex_check_barcode(bcode: str) -> str | None:
    milk8 = r"\s*0100000(?P<barcode>046[0-9]{6})(215.{12}\s*(17\d{6}|7003\d{10})|215.{5}|215.{7})(\s*93.{3}|\s*93.{4}|\s*93.{5})(\s*3103(?P<weight>\d{6}))?"
    milkBelorus = r"\s*01(?P<barcode>04[0-9]{12})(21.{13}\s*(17\d{6}|7003\d{10})|21.{8})(\s*93.{3}|\s*93.{4}|\s*93.{5})(\s*3103(?P<weight>\d{6}))?"
    milkNoName = r"\s*01(?P<barcode>086[0-9]{11})(21.{13}\s*(17\d{6}|7003\d{10})|21.{6}|21.{8})(\s*93.{3}|\s*93.{4}|\s*93.{5})(\s*3103(?P<weight>\d{6}))?"
    milkOld = r"01(?P<barcode>[0-9]{14})21.{6}\s*93.{4}\s*"
    water = r"01(?P<barcode>[0-9]{14})21.{13}\s*93.{4}\s*"
    beer = r"01(?P<barcode>[0-9]{14})21.{7}\s*93.{4}\s*"
    draftbeer = (
        r"01(?P<barcode>[0-9]{14})21.{7}(\x1d|\s*)93.{4}(335[0-6]{1}[0-9]{6}){0,1}\s*"
    )
    tobacco = r"\d{14}.{15}|01(?P<barcode>\d{14})21.{7}8005\d{6}93.{4}.*"
    patterns = [
        milk8,
        milkBelorus,
        milkNoName,
        milkOld,
        water,
        beer,
        draftbeer,
        tobacco,
    ]
    for pattern in patterns:
        if re.search(pattern, bcode):
            return re.search(pattern, bcode).group("barcode")


async def check_text_barcode(
    product: Product,
    goods: _Goods,
    message: Message,
    bcode: str,
    log_e: LoggerEGAIS,
    cash: ForemanCash,
) -> Union[Product, bool]:
    bcode = bcode.strip()
    for p in goods.products:
        if bcode in [p.bcode, p.cis]:
            await message.answer(
                texts.error_head
                + f'Вы уже отправяли данный код "<code>{bcode}</code>"\n'
                f"Отправьте другой товар",
                reply_markup=kb_addbcode_load_prepare_commit(),
            )
            return False
    if product.tmctype in [TmcType.markedgoods, TmcType.draftbeer, TmcType.tobacco]:
        regex_barcode = get_ean_from_gtin(regex_check_barcode(bcode))
        if product.tmctype == TmcType.draftbeer and bcode.isdigit():
            raise ValueError("Отсканируйте код маркировки, а не штрихкод")
        if product.tmctype != TmcType.draftbeer and bcode.isdigit():
            log_e.debug("Состоит только из цифр")
            product.bcode = bcode
        # elif regex_barcode is None:
        elif regex_barcode is not None:
            log_e.debug("Подошел под регулярное выражение")
            znak = TrueApi(inn_to_auth=config.main_inn)
            await znak.create_token()
            pdinfo = (await znak.product_info2([regex_check_barcode(bcode)])).results[0]
            if pdinfo.productGroupId == GroupIds.beer and pdinfo.coreVolume > 0:
                draftbeer = DraftBeerInfo(
                    volume_draftbeer=pdinfo.coreVolume / 1000,
                )
                product.draftbeer = draftbeer

            product.name = pdinfo.name
            product.bcode = regex_barcode
            product.cis = bcode
    else:
        if bcode.isdigit():
            product.bcode = bcode
        else:
            await message.answer(
                texts.error_head
                + f'Отправленный вами код "<code>{bcode}</code>" не является штрихкодом\n'
                f"Попробуйте снова отправить штрихкод",
                reply_markup=one_time_scanner(),
            )
            return False
    try:
        barcode = await ArtixCashDB(cash.ip()).get_barcode(product.bcode)
        if barcode is not None:
            product.price = barcode.price if barcode.price is not None else 0
            product.name = barcode.name
    except OperationalError:
        pass
    return product


async def check_product(
    product: Product, message: Message, state: FSMContext, log_e: LoggerEGAIS
):
    if product:
        await state.update_data(product=product.model_dump_json())
        if product.tmctype == TmcType.draftbeer:
            await state.set_state(AddToCashBarcode.expirationdate_draftbeer)
            date_text = datetime.datetime.now() + datetime.timedelta(days=7)
            await message.answer(
                "Введите предельную дату реализации (Дату когда выходит срок годности)\n"
                f"Пример: <code>{date_text.strftime('%d.%m.%Y')}</code>",
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            if product.price > 0:
                await accept_name(message, state, log_e)
            else:
                await message.answer("Введите цену товара")
                await state.set_state(AddToCashBarcode.price)


async def start_add_bcode(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Добавить штрихкод")
    data = await state.get_data()
    await state.update_data(product=None)
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    if cash.gui_interface == "touch":
        log_e.info("Хотите добавить в графический интерфейс?")
        await call.message.edit_text(
            "Хотите добавить в графический интерфейс?",
            reply_markup=inline.kb_add_to_touch(),
        )
        await state.set_state(AddToCashBarcode.is_touch)
    else:
        log_e.info("Выберите нужный тип товара")
        await call.message.edit_text(
            "Выберите нужный тип товара", reply_markup=inline.kb_addbcode_select_dcode()
        )
        await state.set_state(AddToCashBarcode.dcode)


async def select_is_touch(
    call: CallbackQuery,
    state: FSMContext,
    callback_data: AddToTouchPanel,
    log_e: LoggerEGAIS,
):
    log_e.button(f'Добавить в тач интерфейс "{callback_data.touch}"')
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    if callback_data.touch:
        await call.message.edit_text(
            "Выберите нужную категорию товара",
            reply_markup=inline.kb_main_actionpanel_goods(cash),
        )
    else:
        await call.message.edit_text(
            "Выберите нужный тип товара", reply_markup=inline.kb_addbcode_select_dcode()
        )
        await state.set_state(AddToCashBarcode.dcode)


async def after_select_main_actionpanel(
    call: CallbackQuery,
    state: FSMContext,
    callback_data: ActionpanelGoods,
    log_e: LoggerEGAIS,
):
    log_e.info(f'Выбрали категорию {callback_data.model_dump_json()}"')
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    artix = ArtixCashDB(cash.ip())
    apanelitem = artix.get_actionpanelitem(callback_data.acitem_id)
    apanelparameter = artix.get_actionpanelparameter(apanelitem.actioncode)
    hotkey = artix.get_hotkey(apanelparameter.parametervalue)
    hotkeyinvents = artix.get_hotkeyinvents(hotkey.hotkeycode)
    main_action = _Actionpanelitem(**apanelitem.__dict__)
    await state.update_data(main_action=main_action.model_dump_json())
    if not callback_data.dir:
        tp = TouchPanel(
            actionpanelitem=apanelitem.__dict__,
            actionpanelparameter=(
                apanelparameter.__dict__
                if apanelparameter is not None
                else apanelparameter
            ),
            hotkey=hotkey.__dict__ if hotkey is not None else hotkey,
            hotkeyInvents=(
                [_.__dict__ for _ in hotkeyinvents]
                if hotkeyinvents is not None
                else hotkeyinvents
            ),
            type=(
                UpdateHotkeyType.APPEND
                if callback_data.hk_list
                else UpdateHotkeyType.UPDATE
            ),
        )
        log_e.debug(tp.model_dump_json())
        product = Product(touch=tp)
        if "пиво" in main_action.name.lower():
            product.dcode = Dcode.beer
            product.op_mode = OpMode.beer
            product.tmctype = TmcType.basic
            await state.update_data(product=product.model_dump_json())
            await state.set_state(AddToCashBarcode.measure)
            await call.message.edit_text(
                "Выберите вид продажи\n"
                "<b><u>Поштучный</u></b> - Алкоголь который будете продавать сканировав акцизную марку\n"
                "<b><u>Розлив</u></b> - Алкоголь который продаётся порционно (подойдет для баров)",
                reply_markup=inline.kb_addbcode_select_measure_beer(),
            )

        else:
            await call.message.edit_text(
                "Выберите нужный тип товара",
                reply_markup=inline.kb_addbcode_select_dcode(),
            )
            await state.set_state(AddToCashBarcode.dcode)
        await state.update_data(product=product.model_dump_json())
    else:
        await call.message.edit_text(
            "Выберите нужную позицию",
            reply_markup=inline.kb_select_actionitem(callback_data, cash),
        )


async def select_actionpanelitem(
    call: CallbackQuery,
    state: FSMContext,
    callback_data: ActionPanelItem,
    log_e: LoggerEGAIS,
):
    log_e.info(f'Выбрали actionpanelitem {callback_data.model_dump_json()}"')
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    main_action = _Actionpanelitem.model_validate_json(data["main_action"])
    artix = ArtixCashDB(cash.ip())
    apanelitem = artix.get_actionpanelitem(callback_data.id)
    apanelparameter = artix.get_actionpanelparameter(apanelitem.actioncode)
    hotkey = artix.get_hotkey(apanelparameter.parametervalue)
    hotkeyinvents = artix.get_hotkeyinvents(hotkey.hotkeycode)
    tp = TouchPanel(
        actionpanelitem=apanelitem.__dict__,
        actionpanelparameter=(
            apanelparameter.__dict__ if apanelparameter is not None else apanelparameter
        ),
        hotkey=hotkey.__dict__ if hotkey is not None else hotkey,
        hotkeyInvents=(
            [_.__dict__ for _ in hotkeyinvents]
            if hotkeyinvents is not None
            else hotkeyinvents
        ),
        type=(
            UpdateHotkeyType.APPEND
            if callback_data.hk_list
            else UpdateHotkeyType.UPDATE
        ),
    )
    log_e.debug(tp.model_dump_json())
    product = Product(touch=tp)
    if "пиво" in main_action.name.lower():
        product.dcode = Dcode.beer
        product.op_mode = OpMode.beer
        product.tmctype = TmcType.basic
        await state.update_data(product=product.model_dump_json())
        await state.set_state(AddToCashBarcode.measure)
        await call.message.edit_text(
            "Выберите вид продажи\n"
            "<b><u>Поштучный</u></b> - Алкоголь который будете продавать сканировав акцизную марку\n"
            "<b><u>Розлив</u></b> - Алкоголь который продаётся порционно (подойдет для баров)",
            reply_markup=inline.kb_addbcode_select_measure_beer(),
        )

    else:
        await call.message.edit_text(
            "Выберите нужный тип товара", reply_markup=inline.kb_addbcode_select_dcode()
        )
        await state.set_state(AddToCashBarcode.dcode)
    await state.update_data(product=product.model_dump_json())


async def select_dcode(
    call: CallbackQuery,
    state: FSMContext,
    callback_data: SelectDcode,
    log_e: LoggerEGAIS,
):
    await state.set_state(AddToCashBarcode.measure)
    dcode, op_mode, tmctype = (
        callback_data.dcode,
        callback_data.op_mode,
        callback_data.tmctype,
    )
    data = await state.get_data()
    if data.get("product") is not None:
        product = Product.model_validate_json(data.get("product"))
        product.dcode = dcode
        product.op_mode = op_mode
        product.tmctype = tmctype
    else:
        product = Product(dcode=dcode, op_mode=op_mode, tmctype=tmctype)

    if product.dcode == Dcode.basic:
        log_e.info('Выбрали "Продукты"')
    elif product.tmctype == Dcode.alcohol:
        log_e.info('Выбрали "Алкоголь"')
    elif product.tmctype == Dcode.beer:
        log_e.info('Выбрали "Пиво"')
    elif product.tmctype == Dcode.tobacco:
        log_e.info('Выбрали "Сигареты"')
    elif product.tmctype == Dcode.markirovka:
        log_e.info('Выбрали "Маркировка"')

    if dcode == Dcode.beer:
        await call.message.edit_text(
            "Выберите вид продажи\n"
            "<b><u>Поштучный</u></b> - Алкоголь который будете продавать сканировав акцизную марку\n"
            "<b><u>Розлив</u></b> - Алкоголь который продаётся порционно (подойдет для баров)",
            reply_markup=inline.kb_addbcode_select_measure_beer(),
        )
    elif dcode == Dcode.basic:
        await call.message.edit_text(
            "Выберите вид продажи\n"
            "<b><u>Поштучный</u></b> - Товар который будет продаваться целиком. Например: консерва, шоколад\n"
            "<b><u>Весовой</u></b> - Товар который продаётся порционно. Например: Сыр, рыба, орехи\n"
            "<b><u>Розлив</u></b> - Товар который продаётся порционно. Например: Разливной лимонад\n",
            reply_markup=inline.kb_addbcode_select_measure_products(),
        )
    else:
        await state.set_state(AddToCashBarcode.barcode)
        await call.message.answer(
            texts.scan_photo_or_text, reply_markup=one_time_scanner()
        )
    await state.update_data(product=product.model_dump_json())


async def accept_measure(
    call: CallbackQuery,
    state: FSMContext,
    callback_data: SelectMeasure,
    log_e: LoggerEGAIS,
):
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    product = Product.model_validate_json(data["product"])
    product.measure = callback_data.measure
    product.op_mode = callback_data.op_mode
    product.tmctype = callback_data.tmctype
    product.qdefault = callback_data.qdefault
    if product.tmctype == TmcType.draftbeer and cash.os_name != "bionic":
        product.tmctype = TmcType.markedgoods

    if product.measure == Measure.litr:
        log_e.info('Выбрали "Розлив"')
    elif product.measure == Measure.kg:
        log_e.info('Выбрали "Весовой"')
    elif product.measure == Measure.unit:
        log_e.info('Выбрали "Поштучный"')

    if product.tmctype == TmcType.draftbeer and cash.os_name == "bionic":
        await state.set_state(AddToCashBarcode.barcode)
        await call.message.answer(
            texts.scan_photo_or_text, reply_markup=one_time_scanner()
        )
        inn = cash.get_IP_inn()
        if inn is not None:
            try:
                trueapi = TrueApi(inn_to_auth=inn)
                await trueapi.create_token()
                text = (
                    f"Вам доступно отправка документов в Честный знак, "
                    f"но чтобы постановка на кран делалась в Честном знаке, "
                    f"обратитесь в Тех.Поддержку"
                )
                await call.message.answer(
                    texts.intersum_head + text,
                    reply_markup=inline.kb_whatsapp_url(
                        await texts.error_message_wp(cash, text)
                    ),
                )
            except ZnakAPIError as e:
                if "нет оформленных доверенностей" in str(e):
                    log_e.info(f'ИНН "{inn}" - не обслуживается по МЧД')

    else:
        await state.set_state(AddToCashBarcode.barcode)
        await call.message.answer(
            texts.scan_photo_or_text, reply_markup=one_time_scanner()
        )
    await state.update_data(product=product.model_dump_json())


async def volume_draftbeer(
    call: CallbackQuery,
    state: FSMContext,
    callback_data: VolumeDraftBeer,
    log_e: LoggerEGAIS,
):
    log_e.info(f'Выбрали объем кега "{callback_data.volume}"')
    data = await state.get_data()
    product = Product.model_validate_json(data["product"])
    product.draftbeer.volume_draftbeer = callback_data.volume
    await state.update_data(product=product.model_dump_json())
    await state.set_state(AddToCashBarcode.expirationdate_draftbeer)
    date_text = datetime.datetime.now() + datetime.timedelta(days=7)
    await call.message.edit_text(
        "Введите предельную дату реализации (Дату когда выходит срок годности)\n"
        f"Пример: <code>{date_text.strftime('%d.%m.%Y')}</code>"
    )


async def expirationdate_draftbeer(
    message: Message, state: FSMContext, log_e: LoggerEGAIS
):
    log_e.info(f'Ввели предельную дату реализации "{message.text}"')
    data = await state.get_data()
    product = Product.model_validate_json(data["product"])
    try:
        expdate = datetime.datetime.strptime(message.text, "%d.%m.%Y")
    except ValueError:
        log_e.error("Введенная дата не соответствует формату <b>ДД.ММ.ГГГГ</b>")
        await message.answer(
            texts.error_head
            + "Введенная дата не соответствует формату <b>ДД.ММ.ГГГГ</b>\n"
            "Пример как надо ввести дату: <code>01.02.2024</code>"
        )
        return
    if datetime.datetime.now() > expdate:
        log_e.error("Введенная дата раньше текущей")
        await message.answer(
            texts.error_head + "Введенная дата раньше текущей\n"
            "Пример как надо ввести дату: <code>01.02.2024</code>"
        )
        return
    product.draftbeer.expirationDate = expdate
    await state.set_state(AddToCashBarcode.barcode)
    await state.update_data(product=product.model_dump_json())
    if product.price > 0:
        await accept_name(message, state, log_e)
    else:
        await message.answer("Введите цену товара")
        await state.set_state(AddToCashBarcode.price)


async def one_text_barcode(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    product = Product.model_validate_json(data["product"])
    if message.web_app_data is not None:
        log_e.debug(message.web_app_data.data)
        text = message.web_app_data.data
        log_e.info(f'Отсканировал сканером штрихкод "{text}"')
    else:
        text = message.text
        log_e.info(f'Написали штрихкод(-а) "{text}"')
        if product.tmctype == TmcType.draftbeer:
            await message.answer(
                texts.error_head
                + "Запрещенно писать текстом маркировку, если вы ставите кегу на кран.\n"
                "Пожалуйста воспользуйтесь сканером бота."
            )
            log_e.debug(
                "Выдал ошибку, что нельзя писать текстом маркировку, если вы ставите кегу на кран"
            )
            return

    if data.get("goods_addbcode") is not None:
        goods = _Goods.model_validate_json(data.get("goods_addbcode"))
    else:
        goods = _Goods()
    product = await check_text_barcode(
        product=product,
        goods=goods,
        message=message,
        bcode=text,
        log_e=log_e,
        cash=ForemanCash.model_validate_json(data.get("foreman_cash")),
    )
    await check_product(product, message, state, log_e)


# async def more_one_scanner(message: Message, state: FSMContext, log_e: LoggerEGAIS):
#     data = await state.get_data()
#     product = Product.model_validate_json(data['product'])
#     text = message.web_app_data.data
#     log_e.info(f'Отсканировал сканером штрихкода "{", ".join(text)}"')
#     if data.get('goods_addbcode') is not None:
#         goods = _Goods.model_validate_json(data.get('goods_addbcode'))
#     else:
#         goods = _Goods()


async def photo_barcode(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    chat_id = message.chat.id
    boxnumber_path = os.path.join(config.dir_path, "files", "boxnumbers")
    if not os.path.exists(boxnumber_path):
        os.mkdir(boxnumber_path)
    barcode_path = os.path.join(boxnumber_path, str(chat_id))
    img = await message.bot.get_file(message.photo[-1].file_id)
    if not os.path.exists(barcode_path):
        os.mkdir(barcode_path)
    file = os.path.join(barcode_path, f"barcode_{message.message_id}.jpg")
    await message.bot.download_file(img.file_path, file)

    barcodes_from_img = await read_barcodes_from_image(file)
    barcodes_from_img += await read_datamatrix_from_image(file)
    log_e.info(f'Отсканировал фото "{barcodes_from_img}"')

    if len(barcodes_from_img) == 0:  # Если не нашлись штрихкода на картинке
        await check_file_exist(
            file,
            "На данном фото <b><u>не найдено</u></b> штрихкодов",
            message.bot,
            message,
            log_e,
        )
        return
    elif len(barcodes_from_img) > 1:
        await check_file_exist(
            file,
            "На данном фото найдено <b><u>несколько</u></b> штрихкодов",
            message.bot,
            message,
            log_e,
        )
        return

    if os.path.exists(file):
        await asyncio.sleep(0.20)
        os.remove(file)

    data = await state.get_data()
    product = Product.model_validate_json(data["product"])
    if data.get("goods_addbcode") is not None:
        goods = _Goods.model_validate_json(data.get("goods_addbcode"))
    else:
        goods = _Goods()
    product = await check_text_barcode(
        product=product,
        goods=goods,
        message=message,
        bcode=barcodes_from_img[0],
        log_e=log_e,
        cash=ForemanCash.model_validate_json(data.get("foreman_cash")),
    )
    await check_product(product, message, state, log_e)


async def document_barcode(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    chat_id = message.chat.id
    barcode_path = os.path.join(config.dir_path, "files", "boxnumbers", str(chat_id))
    img = await message.bot.get_file(message.document.file_id)
    if not os.path.exists(barcode_path):
        os.mkdir(barcode_path)
    file = os.path.join(barcode_path, f"barcode_{message.message_id}.jpg")
    await message.bot.download_file(img.file_path, file)

    barcodes_from_img = await read_barcodes_from_image(file)
    barcodes_from_img += await read_datamatrix_from_image(file)
    log_e.info(f'Отсканировал фото "{barcodes_from_img}"')

    if len(barcodes_from_img) == 0:  # Если не нашлись штрихкода на картинке
        await check_file_exist(
            file,
            "На данном фото <b><u>не найдено</u></b> штрихкодов\n"
            "Пришлите новое фото или напишите цифры штрихкода",
            message.bot,
            message,
            log_e,
        )
        return
    elif len(barcodes_from_img) > 1:
        await check_file_exist(
            file,
            "На данном фото найдено <b><u>несколько</u></b> штрихкодов\n"
            "Пришлите новое фото или напишите цифры штрихкода",
            message.bot,
            message,
            log_e,
        )
        return

    if os.path.exists(file):
        await asyncio.sleep(0.20)
        os.remove(file)

    data = await state.get_data()
    product = Product.model_validate_json(data["product"])
    if data.get("goods_addbcode") is not None:
        goods = _Goods.model_validate_json(data.get("goods_addbcode"))
    else:
        goods = _Goods()
    product = await check_text_barcode(
        product=product,
        goods=goods,
        message=message,
        bcode=barcodes_from_img[0],
        log_e=log_e,
        cash=ForemanCash.model_validate_json(data.get("foreman_cash")),
    )
    await check_product(product, message, state, log_e)


async def price(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    price = message.text.replace(",", ".")
    check_price = price.replace(".", "")
    if not check_price.isdecimal():
        log_e.error(f'Цена не только из цифр "{price}"')
        await message.answer(texts.error_price_not_decimal)
        return
    log_e.info(f'Ввели цену товаров "{price}"')
    data = await state.get_data()
    product = Product.model_validate_json(data["product"])
    product.price = price
    await state.update_data(product=product.model_dump_json())
    if product.name:
        await accept_name(message, state, log_e)
    else:
        await state.set_state(AddToCashBarcode.name)
        await message.answer("Напишите название товара")


async def accept_name(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    product = Product.model_validate_json(data["product"])
    if not product.name:
        if message.text is None:
            log_e.error(f'Название не введено "{message.text}"')
            await message.answer(f"Название не введено\n" f"Напишите название снова")
            return
        product.name = message.text
        log_e.info(f'Ввели название товаров "{message.text}"')
    if data.get("goods_addbcode") is not None:
        goods = _Goods.model_validate_json(data.get("goods_addbcode"))
    else:
        goods = _Goods()
    goods.products.append(product)
    product_info = goods.prepare_text()
    for i, text in enumerate(product_info, start=1):
        if i == len(product_info):
            await message.answer(text, reply_markup=inline.kb_addbcode_prepare_commit())
        else:
            await message.answer(text)
    await state.update_data(goods_addbcode=goods.model_dump_json())


async def load_prepare_commit(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    await call.answer()
    log_e.button("Список сканированных товаров")
    data = await state.get_data()
    goods = _Goods.model_validate_json(data.get("goods_addbcode"))
    goods_info = goods.prepare_text()
    for i, text in enumerate(goods_info, start=1):
        if i == len(goods_info):
            await call.message.answer(
                text, reply_markup=inline.kb_addbcode_prepare_commit()
            )
        else:
            await call.message.answer(text)
    await state.update_data(goods_addbcode=goods.model_dump_json())


async def addbcode_commit(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    await call.message.edit_text("Загрузка информации на кассу...")
    data = await state.get_data()
    goods = _Goods.model_validate_json(data.get("goods_addbcode"))
    log_e.debug(goods.model_dump_json())
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    cash_name = f"cash-{cash.shopcode}-{cash.cashcode}"
    artix = ArtixCashDB(cash.ip())
    try:
        await create_more_barcodes(goods, cash_name)
        await add_barcodes_in_cash(cash.ip(), await get_barcodes_for_add(cash_name))
        await artix.add_products_in_cash(goods)
        for product in goods.products:
            await create_goods_log(
                cash_number=cash.shopcode,
                level="SUCCESS",
                type="Добавили",
                inn=data.get("inn"),
                price=product.price,
                otdel=product.dcode.value,
                op_mode=product.op_mode,
                tmctype=product.tmctype.value,
                qdefault=product.qdefault,
                user_id=call.message.chat.id,
            )
        log_e.success(f"Успешно добавлены {len(goods.products)} штриход(-а)")
        log_e.debug(goods.model_dump_json())
        if len(goods.products) == 1:
            await call.message.edit_text(
                "✅Успешно добавлен 1 штрихкод, в течении 5 минут (обычно мгновенно) он будет загружен на кассу"
            )
        else:
            await call.message.edit_text(
                f"✅Успешно добавлен {len(goods.products)} штрихкода(-ов), через 5 минут они будут загружены на кассу"
            )
        await state.update_data(goods_addbcode=None, product=None)

        if TmcType.draftbeer in [product.tmctype for product in goods.products]:
            text = (
                f"{texts.intersum_head}"
                f"Данные кеги не поставленны на учет в Честном знаке.\n"
                f"Для этого нам нужно оформленное от вас МЧД (Машиночитаемая доверенность). Данная услуга является платной и стоит 1500 руб\n"
                f'Нажмите кнопку "<b>Оформить МЧД</b>"'
            )
            if len(cash.inn) == 12:
                ip = f"{cash.artix_shopname} ИНН: {cash.inn}"
            elif len(cash.inn2) == 12:
                ip = f"{cash.artix_shopname2} ИНН: {cash.inn2}"
            else:
                ip = "**Неизвестное**"

            whatsapp_message = (
                "Здравствуйте!\n"
                f"Это компьютер {cash.shopcode}.\n"
                f"Моё ИП: {ip}\n"
                f"Подскажите пожалуйста, что мне нужно сделать чтобы оформить машиночитаемую доверенность?"
            )
            await call.message.answer(
                text,
                reply_markup=inline.kb_whatsapp_url(
                    message=whatsapp_message,
                    button_text="Оформить МЧД",
                    phone="79625631092",
                ),
            )
    except OperationalError as ex:
        await state.update_data(goods_addbcode=None, product=None)
        log_e.exception(ex)
        text = (
            "К сожалению, в данный момент нет соединения с кассой.\n"
            "Пожалуйста, проверьте ваше интернет-соединение.\n"
            "Штрихкоды будут загружены автоматически, через 5 минут после восстановления связи\n"
        )
        msg = await texts.error_message_wp(cash, text)
        await call.message.answer(
            texts.error_head + text, reply_markup=inline.kb_whatsapp_url(msg)
        )


async def read_datamatrix_from_image(image_path) -> list[str]:
    image = cv2.imread(str(image_path))
    barcodes = decode(image)
    barcode_data_list = [barcode.data.decode("utf-8") for barcode in barcodes]
    return barcode_data_list


if __name__ == "__main__":
    a = "\x1d0104607031706336215bIsbIa\x1d933z27"
    print(regex_check_barcode(a))
