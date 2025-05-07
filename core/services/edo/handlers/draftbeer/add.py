import re
from datetime import datetime
from pathlib import Path
from typing import Union

from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.utils.formatting import Bold, as_list, as_key_value, as_marked_section
from aiogram.utils.formatting import Code as CodeText

import config
from core.database.artix.querys import ArtixCashDB
from core.database.model_logs import Level
from core.keyboards.inline import kb_whatsapp_url
from core.keyboards.reply import one_time_scanner
from core.loggers.markirovka_logger import LoggerZnak
from core.services.edo.callback_data import DraftBeerMOD
from core.services.edo.keyboards import inline
from core.services.edo.states import DraftBeerAdd
from core.services.egais.TTN.accept import read_barcodes_from_image
from core.services.egais.goods.draftbeer.pd_model import Profile, DraftBeer, Code
from core.services.egais.goods.pd_models import TmcType, Measure, Dcode, OpMode
from core.services.markirovka.database.query_db import create_edodocuments_log
from core.services.markirovka.enums import GisMtDocType
from core.services.markirovka.trueapi import TrueApi, check_cises
from core.services.markirovka.trueapi import get_ean_from_gtin
from core.utils import texts
from core.utils.foreman.pd_model import ForemanCash
from core.utils.redis import RedisConnection
from core.utils.znak.scanner import read_datamatrix_from_image

router = Router()


def regex_check_barcode(bcode: str) -> str | None:
    draftbeer = (
        r"01(?P<barcode>[0-9]{14})21.{7}(\x1d|\s*)93.{4}(335[0-6]{1}[0-9]{6}){0,1}\s*"
    )
    if re.search(draftbeer, bcode):
        return get_ean_from_gtin(re.search(draftbeer, bcode).group("barcode"))


async def check_text_barcode(
    draftbeer: DraftBeer,
    message: Message,
    bcode: str,
    log_m: LoggerZnak,
    cash: ForemanCash,
) -> Union[Code, None]:
    cis = bcode.strip()
    if cis in [_.cis for _ in draftbeer.codes]:
        await message.answer(
            texts.error_head + f'Вы уже отправяли данный код "<code>{cis}</code>"\n'
            f"Отправьте другой товар",
            reply_markup=inline.kb_draftbeer_add_load_prepare_commit(),
        )
        return
    regex_barcode = regex_check_barcode(cis)
    if regex_barcode is not None:
        log_m.debug("Подошел под регулярное выражение")
        return Code(cis=cis, gtin=regex_barcode)
    else:
        if cash.xapikey is not None:
            log_m.debug("Отправил запрос в ЧЗ")
            cises = await check_cises([cis], cash.xapikey)
            for code in cises.codes:
                if not code.isOwner:
                    await message.answer(
                        texts.error_head
                        + f"Вы не являетесь владельцем данной марки <code>{bcode}</code>\n"
                        f"Попробуйте снова отсканировать или отправить фотограцию маркировки",
                        reply_markup=one_time_scanner(),
                    )

                    return
                elif code.sold:
                    await message.answer(
                        texts.error_head + "Данная маркировка уже продана"
                    )
                    return
            return Code(cis=cis, gtin=cises.codes[0].gtin)
        else:
            raise ValueError("Не найдено кода маркировки.\nПопробуйте снова")


@router.callback_query(F.data == "draftbeer_add")
async def start_add(
    call: CallbackQuery,
    state: FSMContext,
    log_m: LoggerZnak,
    redis_connection: RedisConnection,
):
    data = await state.get_data()
    if data.get("draftbeer") is not None:
        draftbeer = DraftBeer.model_validate_json(data.get("draftbeer"))
        if len(draftbeer.codes) > 0:
            await load_prepare_commit(call, state, log_m)
    log_m.button("Поставить кегу на учет")
    await check_mod(call, state, log_m, redis_connection)


async def check_mod(
    call: CallbackQuery,
    state: FSMContext,
    log_m: LoggerZnak,
    redis_connection: RedisConnection,
):
    data = await state.get_data()
    trueapi = await TrueApi.load_from_redis(redis_connection)
    mods = await trueapi.get_mods()
    user_info = await trueapi.get_user_info()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    profile = Profile(fio=user_info.name, inn=user_info.inn)
    if len(user_info.inn) == 10:
        mod = await mods.get_mod_by_kpp(cash.get_kpp_by_inn(user_info.inn))
        if mod is None:
            await call.message.answer(
                texts.error_head
                + f'У профиля "{user_info.name}" нет МОД (Место осуществления деятельности) с данным КПП "{cash.kpp}"'
            )
            log_m.error(
                f'У профиля "{user_info.name}" нет МОД (Место осуществления деятельности) с данным КПП "{cash.kpp}"'
            )
            return
        log_m.info(f"Автоматически выбран МОД по КПП: {mod.model_dump_json()}")
        draftbeer = DraftBeer(profile=profile, mod=mod)
    else:
        mods.delete_empty_fias()
        mod_18082 = await mods.get_mod_by_address(cash.address2)
        mod_8082 = await mods.get_mod_by_address(cash.address)
        if len(mods.result) == 0:
            await call.message.answer(
                texts.error_head
                + f'У профиля "{user_info.name}" нет МОД (Место осуществления деятельности'
            )
            log_m.error("У профиля нет МОД (Место осуществления деятельности)")
            return
        elif mod_18082 is not None:
            log_m.info(
                f"Автоматически выбран МОД по порту 18082: {mod_18082.model_dump_json()}"
            )
            draftbeer = DraftBeer(profile=profile, mod=mod_18082)
        elif mod_8082 is not None:
            log_m.info(
                f"Автоматически выбран МОД по порту 8082: {mod_8082.model_dump_json()}"
            )
            draftbeer = DraftBeer(profile=profile, mod=mod_8082)

        else:
            log_m.info(f'Вывел адреса "{[m.address for m in mods.result]}"')
            await call.message.edit_text(
                await mods.text_inline(),
                reply_markup=inline.kb_draftbeer_add_mods(mods=mods),
            )
            draftbeer = DraftBeer(profile=profile)
    if draftbeer.mod is not None:
        await state.set_state(DraftBeerAdd.cis)
        await call.message.delete()
        await call.message.answer(
            texts.scan_datamatrix_photo, reply_markup=one_time_scanner()
        )
    await state.update_data(draftbeer=draftbeer.model_dump_json())


@router.callback_query(DraftBeerMOD.filter())
async def after_select_mod(
    call: CallbackQuery,
    state: FSMContext,
    log_m: LoggerZnak,
    callback_data: DraftBeerMOD,
    redis_connection: RedisConnection,
):
    data = await state.get_data()
    draftbeer = DraftBeer.model_validate_json(data["draftbeer"])
    trueapi = await TrueApi.load_from_redis(redis_connection)
    if callback_data.fias:
        mods = await trueapi.get_mods()
        mod = await mods.get_mod_by_fias(callback_data.fias)
    else:
        mods = await trueapi.get_mods()
        mod = await mods.get_mod_by_kpp(callback_data.fias)
    log_m.info(f'Выбрали МОД "{mod.model_dump_json()}"')
    draftbeer.mod = mod
    await state.update_data(draftbeer=draftbeer.model_dump_json())
    await state.set_state(DraftBeerAdd.cis)
    await call.message.delete()
    await call.message.answer(
        texts.scan_datamatrix_photo, reply_markup=one_time_scanner()
    )


@router.message(
    DraftBeerAdd.cis, F.content_type.in_([ContentType.WEB_APP_DATA, ContentType.TEXT])
)
async def scan(
    message: Message,
    state: FSMContext,
    log_m: LoggerZnak,
    redis_connection: RedisConnection,
):
    data = await state.get_data()
    draftbeer = DraftBeer.model_validate_json(data["draftbeer"])
    cash = ForemanCash.model_validate_json(data["foreman_cash"])

    if message.web_app_data is not None:
        text = message.web_app_data.data
        log_m.info(f'Отсканировал сканером штрихкод "{text}"')
    else:
        text = message.text
        log_m.info(f'Написали штрихкод(-а) "{text}"')
        await message.answer(
            texts.error_head + "Запрещенно писать текстом маркировку.\n"
            "Пожалуйста воспользуйтесь сканером бота, или отправьте фото."
        )
        log_m.debug(
            "Выдал ошибку, что нельзя писать текстом маркировку, если вы ставите кегу на кран"
        )
        return
    draftbeerCode = await check_text_barcode(draftbeer, message, text, log_m, cash)
    if draftbeerCode is not None:
        trueapi = await TrueApi.load_from_redis(redis_connection)
        pdinfo = await trueapi.product_info2([draftbeerCode.gtin])
        draftbeerCode.pdinfo = pdinfo.results[0]
        await state.set_state(DraftBeerAdd.prepare_commit)
        cisInfo = await trueapi.get_cises_info([draftbeerCode.cis])
        draftbeerCode.expirationDate = cisInfo[0].cisInfo.expirationDate
        if (
            draftbeerCode.pdinfo.coreVolume == 0
            and int(cisInfo[0].cisInfo.volumeSpecialPack) > 0
        ):
            draftbeerCode.pdinfo.coreVolume = int(cisInfo[0].cisInfo.volumeSpecialPack)
        draftbeer.codes.append(draftbeerCode)
        await state.update_data(draftbeer=draftbeer.model_dump_json())
        product_info = await draftbeer.prepare_commit_text()
        for i, text in enumerate(product_info, start=1):
            if i == len(product_info):
                await message.answer(
                    text, reply_markup=inline.kb_draftbeer_add_prepare_commit()
                )
            else:
                await message.answer(text)
        log_m.debug(draftbeerCode.model_dump_json())


@router.message(
    DraftBeerAdd.cis, F.content_type.in_([ContentType.PHOTO, ContentType.DOCUMENT])
)
async def photo_or_document(
    message: Message,
    state: FSMContext,
    log_m: LoggerZnak,
    redis_connection: RedisConnection,
):
    barcode_path = Path(config.dir_path, "files", "draftbeer_add", str(message.chat.id))
    barcode_path.mkdir(parents=True, exist_ok=True)
    if message.photo is not None:
        img = await message.bot.get_file(message.photo[-1].file_id)
    elif message.document is not None:
        img = await message.bot.get_file(message.document.file_id)
    file = barcode_path / f"barcode_{message.message_id}.jpg"
    await message.bot.download_file(img.file_path, file)
    log_m.info("Начал сканирование фото")
    barcodes_from_img = await read_datamatrix_from_image(file)
    if not barcodes_from_img:
        barcodes_from_img += await read_barcodes_from_image(file)
    log_m.info(f'Отсканировал фото "{barcodes_from_img}"')
    try:
        if len(barcodes_from_img) == 0:  # Если не нашлись штрихкода на картинке
            msg = "На данном фото <b><u>не найдено</u></b> штрихкода"
            await message.bot.send_photo(
                message.chat.id, photo=FSInputFile(file), caption=msg
            )
            log_m.debug(msg)
            file.unlink(missing_ok=True)
            raise ValueError(msg)
        elif len(barcodes_from_img) > 1:
            msg = "На данном фото найдено <b><u>несколько</u></b> штрихкодов"
            await message.bot.send_photo(
                message.chat.id, photo=FSInputFile(file), caption=msg
            )
            log_m.debug(msg)
            file.unlink(missing_ok=True)
            raise ValueError(msg)
        elif barcodes_from_img[0].isdigit():
            msg = (
                "На данном фото найден <b><u>штрихкод</u></b>.\n"
                "Пожалуйста воспользуйтесь сканером бота, или отправьте фотографию и закройте на данном фото штрихкода, оставьте только маркировку."
            )
            await message.bot.send_photo(
                message.chat.id, photo=FSInputFile(file), caption=msg
            )
            log_m.debug(msg)
            file.unlink(missing_ok=True)
            raise ValueError(msg)
    except ValueError as v:
        log_m.error(str(v))
        return
    file.unlink(missing_ok=True)

    data = await state.get_data()
    draftbeer = DraftBeer.model_validate_json(data["draftbeer"])
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    draftbeerCode = await check_text_barcode(
        draftbeer=draftbeer,
        message=message,
        bcode=barcodes_from_img[0],
        log_m=log_m,
        cash=cash,
    )
    if draftbeerCode is not None:
        trueapi = await TrueApi.load_from_redis(redis_connection)
        pdinfo = await trueapi.product_info2([draftbeerCode.gtin])
        draftbeerCode.pdinfo = pdinfo.results[0]
        await state.set_state(DraftBeerAdd.prepare_commit)
        cisInfo = await trueapi.get_cises_info([draftbeerCode.cis])
        draftbeerCode.expirationDate = cisInfo[0].cisInfo.expirationDate
        draftbeer.codes.append(draftbeerCode)
        await state.update_data(draftbeer=draftbeer.model_dump_json())
        product_info = await draftbeer.prepare_commit_text()
        for i, text in enumerate(product_info, start=1):
            if i == len(product_info):
                await message.answer(
                    text, reply_markup=inline.kb_draftbeer_add_prepare_commit()
                )
            else:
                await message.answer(text)
        log_m.debug(draftbeerCode.model_dump_json())


@router.message(DraftBeerAdd.expDate)
async def enter_expiration_date(message: Message, state: FSMContext, log_m: LoggerZnak):
    data = await state.get_data()
    draftbeer = DraftBeer.model_validate_json(data["draftbeer"])
    draftbeerCode = Code.model_validate_json(data["draftbeerCode"])
    log_m.info(f"Ввели дату: {message.text}")
    try:
        expdate = datetime.strptime(message.text, "%d.%m.%Y")
    except ValueError:
        log_m.error("Введенная дата не соответствует формату <b>ДД.ММ.ГГГГ</b>")
        await message.answer(
            texts.error_head
            + "Введенная дата не соответствует формату <b>ДД.ММ.ГГГГ</b>\n"
            "Пример как надо ввести дату: <code>01.02.2024</code>"
        )
        return
    draftbeerCode.expirationDate = expdate
    draftbeer.codes.append(draftbeerCode)
    await state.update_data(draftbeer=draftbeer.model_dump_json())
    await state.set_state(DraftBeerAdd.prepare_commit)
    product_info = await draftbeer.prepare_commit_text()
    for i, text in enumerate(product_info, start=1):
        if i == len(product_info):
            await message.answer(
                text, reply_markup=inline.kb_draftbeer_add_prepare_commit()
            )
        else:
            await message.answer(text)


@router.callback_query(F.data == "send_prepare_commit", DraftBeerAdd.cis)
async def load_prepare_commit(
    call: CallbackQuery, state: FSMContext, log_m: LoggerZnak
):
    data = await state.get_data()
    draftbeer = DraftBeer.model_validate_json(data["draftbeer"])
    log_m.button("Список ранее сканированных кег")
    await state.set_state(DraftBeerAdd.prepare_commit)
    product_info = await draftbeer.prepare_commit_text()
    await call.message.delete()
    for i, text in enumerate(product_info, start=1):
        if i == len(product_info):
            await call.message.answer(
                text, reply_markup=inline.kb_draftbeer_add_prepare_commit()
            )
        else:
            await call.message.answer(text)


@router.callback_query(
    F.data == "commit_draftbeer_add",
    DraftBeerAdd.prepare_commit,
    flags={"long_operation": "typing"},
)
async def commit(
    call: CallbackQuery,
    state: FSMContext,
    log_m: LoggerZnak,
    redis_connection: RedisConnection,
):
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    artix = ArtixCashDB(cash.ip())
    artix.ping()
    await call.message.edit_text(texts.load_information)
    log_m.info('Готово "Разливное Пиво"')
    draftbeer = DraftBeer.model_validate_json(data["draftbeer"])
    trueapi = await TrueApi.load_from_redis(redis_connection)
    doc_id = await trueapi.document_create(
        pg_name="beer",
        product_document=await draftbeer.edo_doc(),
        doctype=GisMtDocType.CONNECT_TAP,
        file_path=await config.draftbeer_path(call.message.chat.id),
    )

    doc_info, ok = await trueapi.wait_gisMt_response(doc_id)
    if ok:
        await create_edodocuments_log(
            user_id=str(call.message.chat.id),
            doc_type=GisMtDocType.CONNECT_TAP,
            doc_id=doc_id,
            fio=draftbeer.profile.fio,
            level=Level.success,
            inn=draftbeer.profile.inn,
        )
        # await create_inventory_log(call.message.chat.id, file_path, inventory)
        await call.message.answer(
            texts.success_head + f"Разливное пиво успешно принято."
        )
        for code in draftbeer.codes:
            ean = get_ean_from_gtin(code.pdinfo.gtin)
            bcode = await artix.get_barcode(ean)
            await artix.insert_draftbeer_ostatki(
                cis=code.cis,
                bcode=ean,
                name=bcode.name if bcode is not None else code.pdinfo.name,
                expirationdate=code.expirationDate,
                connectdate=code.connectDate,
                volume=code.pdinfo.coreVolume / 1000,
            )
            if bcode is None:
                await artix.insert_tmc(
                    code=ean,
                    bcode=ean,
                    dcode=Dcode.beer.value,
                    name=code.pdinfo.name,
                    measure=Measure.unit.value,
                    op_mode=OpMode.beer.value,
                )
                await artix.insert_barcode(
                    code=ean,
                    barcode=ean,
                    name=code.pdinfo.name,
                    measure=Measure.unit.value,
                    quantdefault=0,
                    tmctype=TmcType.draftbeer.value,
                )
            else:
                await artix.update_barcode(
                    barcode=ean, tmctype=TmcType.draftbeer, quantdefault=0
                )
        log_m.success(f'Разливное пиво успешно принято. Статус "{doc_info.status}"')
    else:
        await create_edodocuments_log(
            user_id=str(call.message.chat.id),
            doc_type=GisMtDocType.CONNECT_TAP,
            doc_id=doc_id,
            fio=draftbeer.profile.fio,
            level=Level.error,
            inn=draftbeer.profile.inn,
        )
        error_head = [texts.error_head.strip()]
        for e in doc_info.errors:
            error_head.append(Bold(e))

        info_body = []
        for e in doc_info.errors:
            if e.startswith("218"):
                cis = e.replace(
                    "218: В ГИС МТ уже было зарегистрировано подключение данной единицы продукции ",
                    "",
                )
                cis = cis.replace(" к оборудованию для розлива", "")
                for codes in draftbeer.codes:
                    if cis in codes.cis:
                        info_body.append(
                            as_key_value("Название", CodeText(codes.pdinfo.name))
                        )
                        # info_body.append(as_key_value('Срок годности', CodeText(codes.expirationDate.strftime("%Y-%m-%d"))))
                        info_body.append(
                            as_key_value(
                                "Объем", CodeText(codes.pdinfo.coreVolume / 1000)
                            )
                        )
        if info_body:
            content = as_list(
                *error_head,
                as_marked_section(texts.information_head.strip(), *info_body, marker="➖"),
            )
            await call.message.answer(**content.as_kwargs())
        else:
            text = 'Ошибка при постановке кеги не кран\nОбратитесь в тех поддержку'
            await call.message.answer(error_head + text, reply_markup=kb_whatsapp_url(text))
        log_m.error(
            f'Разливное пиво с ошибкой. Статус "{doc_info.status}" Ошибки: {doc_info.errors}'
        )
    await state.update_data(draftbeer=None)


@router.callback_query(F.data == "more_draftbeer_add", DraftBeerAdd.prepare_commit)
async def add_more(call: CallbackQuery, state: FSMContext, log_m: LoggerZnak):
    log_m.button("Добавить еще")
    await state.set_state(DraftBeerAdd.cis)
    await call.message.delete()
    await call.message.answer(
        texts.scan_datamatrix_photo, reply_markup=one_time_scanner()
    )
