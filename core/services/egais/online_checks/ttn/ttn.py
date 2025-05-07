import json
from pathlib import Path

from aiogram import Router, F
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
from core.database.query_BOT import count_onlinechecks, save_onlinecheck
from core.keyboards import inline
from core.loggers.egais_logger import LoggerEGAIS
from core.services.egais.callbackdata import OverpriceTTN
from core.services.egais.goods.pd_models import Dcode
from core.services.egais.online_checks.states import OnlineChecksTTNState
from core.services.egais.online_checks.ttn.pd_ttn import OnlineCheckTTNOptions
from core.services.markirovka.callbackdata import (
    OnlineCheckTTN,
    cbValut,
    OnlineCheckTTNPage,
    OnlineCheckTTNDcode,
)
from core.utils import texts
from core.utils.CS.cs import CS
from core.utils.CS.pd_onlinecheck import OnlineCheck
from core.utils.documents.docs import Documents
from core.utils.foreman.pd_model import ForemanCash
from core.utils.qr import get_buffer_qr

router = Router()


async def get_last_dirs(path: Path, count_ttns: int = 15, page: int = 1) -> list[Path]:
    dirs = [
        d / "WayBill_v4.xml"
        for d in path.iterdir()
        if d.is_dir()
        if (d / "WayBill_v4.xml").exists()
    ]
    sorted_dirs = sorted(dirs, key=lambda d: d.stat().st_ctime)
    reverse_sorted_dirs = sorted_dirs[
        len(sorted_dirs)
        - page * count_ttns : len(sorted_dirs)
        - ((page - 1) * count_ttns)
    ]
    reverse_sorted_dirs.reverse()
    return reverse_sorted_dirs


@router.callback_query(F.data == "online_check_ttn")
async def select_ttn(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Алкогольные накладные")
    await call.message.edit_text(texts.load_information)
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    ttns_path = Path(config.server_path, "exchange", cash.inn, cash.kpp)
    list_ttns = await get_last_dirs(path=ttns_path, page=1)
    wbs = await Documents(list_ttns).wb_model()
    await call.message.edit_text(
        "Выберите накладную", reply_markup=inline.kb_online_check_select_ttn(wbs)
    )
    log_e.info(f"Вывел список накладных {[w.ttn_info.number for w in wbs]}")
    await state.update_data(
        online_ttn_options=OnlineCheckTTNOptions(overprice_ttn=0).model_dump_json()
    )


@router.callback_query(OnlineCheckTTNPage.filter())
async def select_ttn_with_page(
    call: CallbackQuery,
    state: FSMContext,
    log_e: LoggerEGAIS,
    callback_data: OnlineCheckTTNPage,
):
    log_e.button(f"Алкогольные накладные страница {callback_data.page}")
    await call.message.edit_text(texts.load_information)
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    ttns_path = Path(config.server_path, "exchange", cash.inn, cash.kpp)
    list_ttns = await get_last_dirs(path=ttns_path, page=callback_data.page)
    wbs = await Documents(list_ttns).wb_model()
    await call.message.edit_text(
        "Выберите накладную",
        reply_markup=inline.kb_online_check_select_ttn(
            wbs4=wbs,
            page=callback_data.page,
        ),
    )
    log_e.info(f"Вывел список накладных {[w.ttn_info.number for w in wbs]}")


@router.callback_query(OnlineCheckTTN.filter())
async def online_check_ttn(
    call: CallbackQuery,
    state: FSMContext,
    log_e: LoggerEGAIS,
    callback_data: OnlineCheckTTN,
):
    log_e.info(f"Выбрал накладную {callback_data.ttn_e}")
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    ttn_path = Path(
        config.server_path,
        "exchange",
        cash.inn,
        cash.kpp,
        callback_data.ttn_e,
        "WayBill_v4.xml",
    )
    wb = await Documents([ttn_path]).wb_model()
    ttn_options = OnlineCheckTTNOptions.model_validate_json(
        data.get("online_ttn_options")
    )
    ttn_options.wb_path = ttn_path
    await state.update_data(online_ttn_options=ttn_options.model_dump_json())
    texts = wb[0].bot_text()
    for i, txt in enumerate(texts, start=1):
        if i == 1:
            await call.message.edit_text(
                txt, reply_markup=inline.kb_online_check_with_check()
            )
        else:
            await call.message.answer(txt)


@router.callback_query(F.data == "overprice_oc_ttn")
async def overprice_oc_ttn(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Добавить наценку на товар")
    await call.message.edit_text(
        "Выберите процент, на который увеличиться стоимость товаров",
        reply_markup=inline.kb_select_procent_overprice(),
    )


@router.callback_query(F.data == "enter_overprice_ttn")
async def prepare_enter_overprice(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    log_e.button("Напечатать самому")
    await call.message.edit_text(
        "Напишите процент ответным сообщением, на который нужно увеличить стоимость"
    )
    await state.set_state(OnlineChecksTTNState.enter_overprice)


@router.message(OnlineChecksTTNState.enter_overprice)
async def enter_overprice_ttn(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.info(f"Написал процент {message.text}")
    data = await state.get_data()
    ttn_options = OnlineCheckTTNOptions.model_validate_json(
        data.get("online_ttn_options")
    )

    wb = (await Documents([Path(ttn_options.wb_path)]).wb_model())[0]
    await wb.overprice(float(message.text))

    ttn_options.overprice_ttn = float(message.text)
    await state.update_data(online_ttn_options=ttn_options.model_dump_json())

    texts = wb.bot_text()
    for i, txt in enumerate(texts, start=1):
        if i == 1:
            await message.answer(txt, reply_markup=inline.kb_online_check_with_check())
        else:
            await message.answer(txt)
    await state.set_state(OnlineChecksTTNState.prepare_commit)


@router.callback_query(OverpriceTTN.filter())
async def select_overprice(
    call: CallbackQuery,
    state: FSMContext,
    log_e: LoggerEGAIS,
    callback_data: OverpriceTTN,
):
    log_e.info(f"Выбрал процент {callback_data.procent}")
    data = await state.get_data()
    ttn_options = OnlineCheckTTNOptions.model_validate_json(
        data.get("online_ttn_options")
    )

    wb = (await Documents([Path(ttn_options.wb_path)]).wb_model())[0]
    await wb.overprice(callback_data.procent)

    ttn_options.overprice_ttn = callback_data.procent
    await state.update_data(online_ttn_options=ttn_options.model_dump_json())

    texts_wb = wb.bot_text()
    for i, txt in enumerate(texts_wb, start=1):
        if i == 1:
            await call.message.edit_text(
                txt, reply_markup=inline.kb_online_check_with_check()
            )
        else:
            await call.message.answer(txt)


@router.callback_query(F.data == "continue_oc_ttn")
async def continue_oc_ttn(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Продолжить")
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    valutes = await ArtixCashDB(cash.ip()).get_all_valuts()
    await call.message.edit_text(
        "Выберите тип списания",
        reply_markup=inline.kb_onlinecheck_ttn_ofd(Dcode.alcohol),
    )


@router.callback_query(OnlineCheckTTNDcode.filter())
async def dcode(
    call: CallbackQuery,
    state: FSMContext,
    log_e: LoggerEGAIS,
    callback_data: OnlineCheckTTNDcode,
):
    log_e.info(f"Выбрал тип списания {Dcode(callback_data.dcode)}")
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    valutes = await ArtixCashDB(cash.ip()).get_all_valuts()
    await state.update_data(oc_ttn_dcode=callback_data.dcode)
    await state.set_state(OnlineChecksTTNState.valut)
    await call.message.edit_text(
        "Выберите тип оплаты", reply_markup=inline.kb_valutes(valutes)
    )


@router.callback_query(cbValut.filter(), OnlineChecksTTNState.valut)
async def valute(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS, callback_data: cbValut
):
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    ttn_options = OnlineCheckTTNOptions.model_validate_json(
        data.get("online_ttn_options")
    )

    valut = await ArtixCashDB(cash.ip()).get_valut(callback_data.code)
    log_e.info(f'Выбрал валюту "{valut.name}"')

    wb = (await Documents([Path(ttn_options.wb_path)]).wb_model())[0]
    await wb.overprice(ttn_options.overprice_ttn)

    onlinecheck_document = wb.onlinecheck_document(valut, ttn_options.dcode)
    onlinecheck = OnlineCheck(
        shopcode=cash.shopcode,
        cashcode=cash.cashcode,
        document=onlinecheck_document.model_dump_json(),
    )

    cs = CS()
    cs_onlinecheck = await cs.create_onlinecheck(onlinecheck)
    await save_onlinecheck(
        cs_onlinecheck.get("id"),
        str(call.from_user.id),
        cash.shopcode,
        cash.cashcode,
        onlinecheck.documentid,
    )
    await call.message.delete()
    wb_texts = wb.bot_text(media=True)
    for i, txt in enumerate(wb_texts, start=1):
        if i == 1:
            await call.message.bot.send_photo(
                call.message.chat.id,
                photo=BufferedInputFile(
                    await get_buffer_qr(f"check-{onlinecheck.documentid}"),
                    filename=f"check-{onlinecheck.documentid}.png",
                ),
                caption=(
                    f"<b>Онлайн-чек</b>: <code>{onlinecheck.documentid}</code>\n{txt}"
                ),
            )
        else:
            await call.message.answer(txt)
    log_e.success(f'Создана накладная как онлайн-чек: "{onlinecheck.documentid}"')
