from aiogram import Bot, flags
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile

import config
from core.loggers.markirovka_logger import LoggerZnak
from core.services.edo.schemas.login.models import Certificate
from core.services.markirovka.callbackdata import ChoisePG
from core.services.markirovka.keyboard.inline import kb_ostatki_actual_menu
from core.services.markirovka.ofdplatforma import get_pg_info
from core.services.markirovka.states import MarkirovkaMenu
from core.services.markirovka.utils.operation_with_csv import (
    check_excel_ostatki_files_for_errors,
)
from core.services.markirovka.trueapi import TrueApi
from core.utils import texts


async def start_actual(call: CallbackQuery, state: FSMContext, log_m: LoggerZnak):
    log_m.button("Актульные остатки")
    data = await state.get_data()
    await call.message.edit_text(
        "Выберите способ получение остатков",
        reply_markup=await kb_ostatki_actual_menu(data["product_groups"], []),
    )
    await state.set_state(MarkirovkaMenu.ostatki_actual)


async def choise_product_group(
    call: CallbackQuery, state: FSMContext, log_m: LoggerZnak, callback_data: ChoisePG
):
    data = await state.get_data()
    groups = data.get("ostatki_groups", [])
    if groups is None:
        groups = []
    if callback_data.name not in groups:
        log_m.info(f'Выбрали товарную группу "{callback_data.name}"')
        groups.append(callback_data.name)
    else:
        log_m.info(f'Убрали товарную группу "{callback_data.name}"')
        groups.remove(callback_data.name)
    await state.update_data(ostatki_groups=groups)
    await call.message.edit_text(
        "Выберите спостоб получение остатков",
        reply_markup=await kb_ostatki_actual_menu(data["product_groups"], groups),
    )


async def select_all_product_groups(
    call: CallbackQuery, state: FSMContext, log_m: LoggerZnak
):
    log_m.button("Выбрать все позиции остатков")
    data = await state.get_data()
    await state.update_data(ostatki_groups=data["product_groups"])
    await call.message.edit_text(
        "Выберите спостоб получение остатков",
        reply_markup=await kb_ostatki_actual_menu(
            data["product_groups"], data["product_groups"]
        ),
    )


async def send_select_actual_ostatki(
    call: CallbackQuery, state: FSMContext, bot: Bot, log_m: LoggerZnak
):
    if not config.develope_mode:
        await call.message.edit_text("Загрузка остатков...")
    data = await state.get_data()
    cert = Certificate.model_validate_json(data["certificate"])
    await state.update_data(ostatki_groups=[])
    znak = TrueApi(
        token=cert.get_token_chz().token,
        thumbprint=cert.thumbprint,
        inn_to_auth=cert.inn,
    )
    path_to_save = config.ostatki_path(str(call.message.from_user.id))
    if config.develope_mode:
        log_m.debug("Начало загрузки остатков")
    excel_files = await znak.get_ostatki_files(path_to_save, data["ostatki_groups"])
    if config.develope_mode:
        log_m.debug(f"Файлы остатков: {excel_files}")
    success_excel_files = await check_excel_ostatki_files_for_errors(
        call.message, excel_files, log_m
    )
    if config.develope_mode:
        log_m.debug(f"Успешные файлы: {excel_files}")
    for e_file in success_excel_files:
        text_info = (
            f"<b>Товарная группа</b>: {e_file.pg_name}\n"
            f"<b>Позиций</b>: {e_file.count_positions}\n"
        )
        await bot.send_document(
            call.message.chat.id,
            document=FSInputFile(e_file.excel_path),
            caption=texts.information_head + text_info,
        )
        await state.update_data(certificate=cert.model_dump_json())


async def ostatki_choice_product_group(
    call: CallbackQuery, state: FSMContext, log_m: LoggerZnak
):
    await call.answer(texts.develop)
