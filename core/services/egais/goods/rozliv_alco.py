from datetime import datetime, timedelta
from pathlib import Path
import paramiko
import socket

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile, CallbackQuery, ReplyKeyboardRemove

import config
from core.database.artix.querys import ArtixCashDB
from core.database.query_BOT import create_goods_log
from core.keyboards import inline
from core.keyboards.reply import one_time_scanner
from core.loggers.egais_logger import LoggerEGAIS
from core.services.egais.TTN.accept import read_barcodes_from_image
from core.services.egais.goods.create_barcodes import read_datamatrix_from_image
from core.services.egais.goods.pd_models import (
    TmcType,
    OpMode,
    DraftBeerInfo,
    RozlivAlco,
    Dcode,
    Measure,
)
from core.services.egais.states import RozlivAlcoState
from core.utils import texts
from core.utils.foreman.pd_model import ForemanCash


async def start_scan_bcode(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Разливной алкоголь")
    data = await state.get_data()
    await state.set_state(RozlivAlcoState.bcode)
    if data.get("rozlivalco") is not None:
        rozlivalco = RozlivAlco.model_validate_json(data.get("rozlivalco"))
        if len(rozlivalco.goods) > 0:
            await load_prepare_commit(call, state, log_e)
            return
    await call.message.delete()
    await call.message.answer(texts.scan_photo_or_text, reply_markup=one_time_scanner())


async def get_barcode(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    msg = "Введите цифры акцизной марки"
    if message.photo is None and message.document is None:
        if message.web_app_data is not None:
            log_e.debug(message.web_app_data.data)
            bcode = message.web_app_data.data
            log_e.info(f'Отсканировал сканером штрихкод "{bcode}"')
        else:
            bcode = message.text
            if not bcode.isdigit():
                log_e.error(f'Штрихкод не только из цифр "{bcode}"')
                await message.answer(
                    texts.error_head + "Штрихкод должен состоять только из цифр"
                )
                return
            log_e.info(f'Написали штрихкод(-а) "{bcode}"')
    else:
        log_e.info("Начал сканирование фото")
        bcode = await get_barcodes_from_photo(message, log_e)
        if bcode is None:
            return
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    artix = ArtixCashDB(cash.ip())
    barcode = await artix.get_barcode(bcode)
    if barcode is None:
        await message.answer(
            f"{texts.error_head}Такого штрихкода нет в базе\n"
            "Нажмите кнопку <b>Добавить товар</b>",
            reply_markup=inline.kb_rozlivalco_not_found_barcode(),
        )
        return
    rozlivalco = DraftBeerInfo(
        bcode=bcode,
        name=barcode.name,
        expirationDate=datetime.now() + timedelta(days=365 * 10),
    )
    await message.bot.send_photo(
        message.chat.id,
        photo=FSInputFile(str(Path(config.dir_path, "files", "example_amark.png"))),
        caption=msg,
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.update_data(rozlivalco_good=rozlivalco.model_dump_json())
    await state.set_state(RozlivAlcoState.amark)


async def get_amark(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.info(f'Ввели акцизную марку "{message.text}"')
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    artix = ArtixCashDB(cash.ip())
    find_amark = await artix.get_excise_from_whitelist(message.text)
    if find_amark is None:
        msg = (
            f"Не найдено акцизной марки в белом списке <code>{message.text}</code>\n"
            f"Попробуйте снова отправить марку, или обратитесь в службу поддержки"
        )
        await message.answer(msg, reply_markup=inline.kb_whatsapp_url(msg))
        log_e.error(f"Не найдено акцизной марки в белом списке {message.text}")
        return
    data = await state.get_data()
    rozlivalco_good = DraftBeerInfo.model_validate_json(data.get("rozlivalco_good"))
    if data.get("rozlivalco"):
        rozlivalco = RozlivAlco.model_validate_json(data.get("rozlivalco"))
        if find_amark.excisemarkid in [g.cis for g in rozlivalco.goods]:
            log_e.error(
                f'Данную акцизную марку "{find_amark.excisemarkid}" вы уже сканировали ранее\n'
                f"Отправьте пожалуйста новую акцизную марку"
            )
            await message.answer(
                texts.error_head + "Данную акцизную марку вы уже сканировали ранее",
                reply_markup=inline.kb_rozlivalco_dubl_amark(),
            )
            return
    rozlivalco_good.cis = find_amark.excisemarkid
    await state.update_data(rozlivalco_good=rozlivalco_good.model_dump_json())
    await state.set_state(RozlivAlcoState.quantity)
    await message.answer("Напишите объем бутылки\n" "Пример: 0.75")


async def volume(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    vol = message.text.replace(",", ".")
    check_price = vol.replace(".", "")
    if not check_price.isdecimal():
        log_e.error(f'Обьем не только из цифр "{vol}"')
        await message.answer(texts.error_price_not_decimal)
        return
    log_e.info(f'Ввели обьем бутылки "{vol}"')
    data = await state.get_data()
    rozlivalco_good = DraftBeerInfo.model_validate_json(data.get("rozlivalco_good"))
    rozlivalco_good.volume_draftbeer = vol
    if data.get("rozlivalco") is not None:
        rozlivalco = RozlivAlco.model_validate_json(data.get("rozlivalco"))
        rozlivalco.goods.append(rozlivalco_good)
        await state.update_data(rozlivalco=rozlivalco.model_dump_json())
    else:
        rozlivalco = RozlivAlco()
        rozlivalco.goods.append(rozlivalco_good)
        await state.update_data(rozlivalco=rozlivalco.model_dump_json())
    await state.set_state(RozlivAlcoState.prepare_commit)
    prepare_text = rozlivalco.prepare_text()
    log_e.info(rozlivalco.model_dump_json())
    for i, text in enumerate(prepare_text, start=1):
        if i == len(prepare_text):
            await message.answer(
                text, reply_markup=inline.kb_rozlivalco_prepare_commit()
            )
        else:
            await message.answer(text)
    await state.update_data(rozlivalco_good=None)


async def load_prepare_commit(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    data = await state.get_data()
    rozlivalco = RozlivAlco.model_validate_json(data.get("rozlivalco"))
    await state.set_state(RozlivAlcoState.prepare_commit)
    prepare_text = rozlivalco.prepare_text()
    log_e.info(rozlivalco.model_dump_json())
    await call.message.delete()
    for i, text in enumerate(prepare_text, start=1):
        if i == len(prepare_text):
            await call.message.answer(
                text, reply_markup=inline.kb_rozlivalco_prepare_commit()
            )
        else:
            await call.message.answer(text)


async def more_alco(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Добавить еще")
    await state.set_state(RozlivAlcoState.bcode)
    await call.message.delete()
    await call.message.answer(texts.scan_photo_or_text, reply_markup=one_time_scanner())


async def commit(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    await call.message.delete()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    rozlivalco = RozlivAlco.model_validate_json(data.get("rozlivalco"))
    for g in rozlivalco.goods:
        artix = ArtixCashDB(cash.ip())
        try:
            await artix.insert_draftbeer_ostatki(
                cis=g.cis,
                bcode=g.bcode,
                volume=g.volume_draftbeer,
                # volume=g.volume_draftbeer * 1000,
                name=g.name,
                expirationdate=g.expirationDate,
                connectdate=g.connectDate,
            )
            # if await artix.get_unit_by_frunit(40) is None:
            #     await artix.insert_unit(
            #         name='Миллилитр',
            #         flag=1,
            #         frunit=40
            #     )
            await artix.update_barcode(
                barcode=g.bcode,
                measure=Measure.litr.value,
                quantdefault=0,
                minprice=1,
                minretailprice=1,
                tmctype=TmcType.draftbeer.value,
            )
            await artix.update_tmc(
                bcode=g.bcode,
                minprice=1,
                minretailprice=1,
                op_mode=OpMode.basic.value,
            )

        except ConnectionError:
            log_e.error("Не удалось подключиться к базе")
            await call.message.answer(
                f"{texts.error_head}"
                f"Не удалось подключиться к кассе\n"
                f"Убедитесь что касса включена, и в кассе есть интернет\n"
                f'Затем попробуйте еще раз нажать "Готово"'
            )
            return
        if not config.develope_mode:
            await create_goods_log(
                cash_number=cash.shopcode,
                level="SUCCESS",
                type="Разливной алкоголь",
                inn=cash.inn,
                price="0",
                otdel=Dcode.alcohol.value,
                op_mode=OpMode.alcohol.value,
                tmctype=TmcType.alcohol.value,
                qdefault="0",
                user_id=call.message.chat.id,
                description=g.cis,
            )
    for i, text in enumerate(rozlivalco.prepare_text(), start=1):
        await call.message.answer(text)
    log_e.debug(rozlivalco.model_dump_json())
    log_e.success("Разливной алкоголь успешно добавлен")
    await state.update_data(rozlivalco=None, rozlivalco_good=None)
    await call.message.answer(
        texts.success_head + "Разливной алкоголь успешно добавлен"
    )


async def get_barcodes_from_photo(message: Message, log_e: LoggerEGAIS) -> str | None:
    barcode_path = Path(config.dir_path, "files", "rozlivalco", str(message.chat.id))
    barcode_path.mkdir(parents=True, exist_ok=True)
    if message.photo is not None:
        image = await message.bot.get_file(message.photo[-1].file_id)
    elif message.document is not None:
        image = await message.bot.get_file(message.document.file_id)
    else:
        await message.answer(texts.error_head + "Нужно отправить фото")
        return
    file = barcode_path / f"barcode_{message.message_id}.jpg"
    await message.bot.download_file(image.file_path, file)
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
