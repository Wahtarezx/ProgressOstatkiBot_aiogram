import asyncio
import json
import os
from collections import Counter
from datetime import datetime

from aiogram import Bot, flags
from aiogram.exceptions import TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.utils.formatting import Bold, Code, Underline, as_line
from funcy import first, where

import config
from core.keyboards.reply import scanner
from core.loggers.markirovka_logger import LoggerZnak
from core.services.edo.schemas.login.models import Certificate
from core.services.markirovka.callbackdata import ChoisePG, ChoiseAction
from core.services.markirovka.database.query_db import (
    select_last_inventory_log,
    create_inventory_log,
)
from core.services.markirovka.enums import GisMtDocType
from core.services.markirovka.inventory.models import Inventory, ProductVolume, CIS
from core.services.markirovka.keyboard.inline import (
    kb_choice_product_group,
    kb_actions,
    kb_scan_inventory,
    kb_confirm_inventory_end,
)
from core.services.markirovka.ofdplatforma import get_pg_info
from core.services.markirovka.states import MarkirovkaMenu
from core.services.markirovka.utils.gtins import check_cises
from core.services.markirovka.utils.operation_with_csv import (
    check_excel_ostatki_files_for_errors,
)
from core.services.markirovka.trueapi import TrueApi, get_actions, get_ean_from_gtin
from core.utils import texts

lock = asyncio.Lock()


async def choice_product_group(
    call: CallbackQuery, state: FSMContext, log_m: LoggerZnak
):
    log_m.button("Инвентаризация")
    data = await state.get_data()
    await call.message.edit_text(
        "Выберите категорию товара для которой будет происходить инвентаризация",
        reply_markup=await kb_choice_product_group(data["product_groups"]),
    )
    await state.set_state(MarkirovkaMenu.inventory_choise_pg)


async def choise_action(
    call: CallbackQuery, state: FSMContext, callback_data: ChoisePG, log_m: LoggerZnak
):
    log_m.info(f'Выбрали категорию "{callback_data.name}"')
    await state.update_data(
        inventory_pg_id=callback_data.id,
        inventory_pg_name=callback_data.name,
        is_volume_balance=callback_data.i_v_b,
    )
    await call.message.edit_text(
        "Выберите причину",
        reply_markup=await kb_actions(callback_data.name, callback_data.id),
    )


@flags.chat_action(action="upload_document", interval=3)
async def start_inventory(
    call: CallbackQuery,
    state: FSMContext,
    callback_data: ChoiseAction,
    log_m: LoggerZnak,
):
    log_m.info(f'Выбрали причину "{callback_data.action}"')
    data = await state.get_data()
    await call.message.edit_text("Загрузка остатков...")
    save_path = config.ostatki_path(str(call.message.from_user.id))
    cert = Certificate.model_validate_json(data["certificate"])
    znak = TrueApi(token=cert.get_token_chz().token, thumbprint=cert.thumbprint)
    response = await znak.get_ostatki_files(save_path, [data["inventory_pg_name"]])
    excel_files = await check_excel_ostatki_files_for_errors(
        call.message, response, log_m
    )
    if excel_files:
        await state.set_state(MarkirovkaMenu.inventory_start)
        doc_info = first(
            where(
                get_actions(data["is_volume_balance"])["docs"],
                action=callback_data.action,
            )
        )
        last_id = (await select_last_inventory_log(cert.inn)).id + 1
        await state.update_data(
            inventory_chz=Inventory(
                pg_name=data["inventory_pg_name"],
                inn=cert.inn,
                action=callback_data.action,
                action_date=datetime.now().strftime("%Y-%m-%d"),
                document_type=doc_info["document_type"],
                document_number=last_id,
                document_date=datetime.now().strftime("%Y-%m-%d"),
                products_balance=excel_files[0].products,
            ).model_dump_json(by_alias=True)
        )
        await call.message.delete()
        await call.message.answer(
            "Можете начинать сканирование марок", reply_markup=scanner()
        )
    else:
        await call.message.answer(
            texts.error_head
            + "Сканирование инвентаризации для данной товарной группы недоступно"
        )
    await state.update_data(certificate=cert.model_dump_json())


async def scanned_inventory(message: Message, state: FSMContext, log_m: LoggerZnak):
    async with lock:
        data = await state.get_data()
        inventory = Inventory.model_validate_json(data["inventory_chz"])
        inventory_pg_name = data["inventory_pg_name"]
        cert = Certificate.model_validate_json(data["certificate"])
        znak = TrueApi(token=cert.get_token_chz().token, thumbprint=cert.thumbprint)
        cises = await get_cises_from_message(
            message, log_m, inventory, znak, inventory_pg_name
        )
        log_m.debug(f"Марки прошли проверку {cises}")

        for gtin, gtin_quantity in Counter([c.gtin for c in cises]).items():
            current_cis = [c for c in cises if c.gtin == gtin]
            find = False

            for p in inventory.products_inventory:
                if p.gtin == gtin:
                    find = True
                    if not p.name:
                        p.name = current_cis[0].name
                    p.gtin_quantity += gtin_quantity
                    for c in current_cis:
                        p.cises.append(c)
            if not find:
                inventory.products_inventory.append(
                    ProductVolume(
                        gtin=gtin,
                        name=current_cis[0].name,
                        gtin_quantity=gtin_quantity,
                        cises=current_cis,
                    )
                )

        await state.update_data(inventory_chz=inventory.model_dump_json())
        messages = texts.markirovka_inventory_info(inventory)
        for count, text in enumerate(messages, start=1):
            if len(messages) != count:
                await message.edit_text(**text.as_kwargs())
            else:
                await message.answer(
                    **text.as_kwargs(), reply_markup=kb_scan_inventory()
                )


async def more_scanned_info(call: CallbackQuery, state: FSMContext, log_m: LoggerZnak):
    if call.message.document is None:
        await call.message.edit_text("Загрузка...")
    data = await state.get_data()
    log_m.button("Подбробная информация инвентаризации")
    save_path = os.path.join(
        config.inventory_dir_path(str(call.message.chat.id)),
        f"info_{datetime.now().strftime('%Y-%m-%d__%H_%M_%S')}.xlsx",
    )
    inventory = Inventory.model_validate_json(data["inventory_chz"])
    inventory_file = await inventory.create_excel_actual_progress(save_path)
    text = await texts.markirovka_inventory_more_info(inventory_file)
    await call.message.delete()
    await call.message.bot.send_document(
        call.message.chat.id,
        document=FSInputFile(inventory_file.excel_path),
        caption=text,
        reply_markup=kb_scan_inventory(True),
    )


async def confirm_inventory_end(
    call: CallbackQuery, state: FSMContext, bot: Bot, log_m: LoggerZnak
):
    if call.message.document is None:
        await call.message.edit_text("Загрузка...")
    data = await state.get_data()
    log_m.button("Подбробная информация инвентаризации")
    save_path = os.path.join(
        config.inventory_dir_path(str(call.message.chat.id)),
        f"{datetime.now().strftime('%Y-%m-%d__%H_%M_%S')}.xlsx",
    )
    inventory = Inventory.model_validate_json(data["inventory_chz"])
    inventory_file = await inventory.create_excel_withdraw(save_path)
    text = await texts.markirovka_inventory_confirm_info(inventory_file)
    await call.message.delete()
    await bot.send_document(
        call.message.chat.id,
        document=FSInputFile(inventory_file.excel_path),
        caption=text,
        reply_markup=kb_confirm_inventory_end(),
    )

    # for count, message in enumerate(messages, start=1):
    #     if len(messages) != count:
    #         await call.message.edit_text(**message.as_kwargs())
    #     else:
    #         await call.message.answer(**message.as_kwargs(),
    #                                   reply_markup=kb_confirm_inventory_end())


async def end_inventory(call: CallbackQuery, state: FSMContext, log_m: LoggerZnak):
    # await call.message.delete()
    log_m.button("Подтвердили завершение инвентаризации")
    await call.message.answer("Загрузка...")
    data = await state.get_data()
    cert = Certificate.model_validate_json(data["certificate"])
    znak = TrueApi(token=cert.get_token_chz().token, thumbprint=cert.thumbprint)
    inventory = Inventory.model_validate_json(data["inventory_chz"])
    file_path = config.inventory_dir_path(str(call.message.from_user.id))
    file_path = os.path.join(file_path, f"{datetime.now().isoformat()}.txt")
    pg_info = await get_pg_info(inventory.pg_name)
    doctype = (
        GisMtDocType.LK_GTIN_RECEIPT
        if data["is_volume_balance"]
        else GisMtDocType.LK_RECEIPT
    )
    doc_id = await znak.document_create(
        pg_name=inventory.pg_name,
        product_document=inventory.get_withdrawal_inventory(
            pg_info.is_volume_balance, True
        ),
        doctype=doctype,
        file_path=file_path,
    )
    status, ok = await znak.wait_gisMt_response(doc_id)
    if ok:
        await create_inventory_log(call.message.chat.id, file_path, inventory)
        log_m.success(f'Успешно принята инвентаризация. Статус "{status}"')
    else:
        log_m.error(f'Инвентаризация с ошибкой. Статус "{status}"')
    text = texts.succes_inventory if ok else texts.error_head
    text += f"<b>Статус документа</b>: <code>{status}</code>"
    await call.message.answer(text)


async def check_cises_errors(
    cises: list,
    inventory: Inventory,
    message: Message,
    znak: TrueApi,
    inventory_pg_name: str,
    log_m: LoggerZnak,
) -> list:
    try:
        result = []
        # Проверка на валидные маркировки
        cises = await check_cises(cises, znak)
        for cis in cises.error:
            content = as_line(
                texts.error_head.strip(),
                Bold(
                    "Данное значение не является маркированным товаром и не будет учтёно в инвентаризации"
                ),
                as_line(Underline("Значение:"), Code(cis), sep=" ", end=""),
                sep="\n",
            )
            log_m.debug(f"Не валидная марка {cis}")
            await message.answer(**content.as_kwargs())
            await asyncio.sleep(1)
        # Уже сканировали до этого
        not_dubl_cises = []
        for cis in cises.access:
            if cis.cis in [
                c.cis for p in inventory.products_inventory for c in p.cises
            ]:
                text = as_line(
                    texts.intersum_head.strip(),
                    Underline(Bold("Данный товар не будет учтён в инвентаризации")),
                    Bold("Вы уже сканировали данный товар"),
                    as_line(Underline("Название:"), Code(cis.name), sep=" ", end=""),
                    as_line(
                        Underline("Штрихкод:"),
                        Code(get_ean_from_gtin(cis.gtin)),
                        sep=" ",
                        end="",
                    ),
                    as_line(
                        Underline("Маркировка:"), Code(Code(cis.cis)), sep=" ", end=""
                    ),
                    sep="\n",
                )
                log_m.debug(f"Уже сканировали марку {cis.cis}")
                await message.answer(**text.as_kwargs())
                await asyncio.sleep(1)
            else:
                not_dubl_cises.append(cis)
        # С выбранной товарной группы
        correct_pg_name = []
        for cis in not_dubl_cises:
            if cis.pg_name != inventory_pg_name:
                text = as_line(
                    texts.intersum_head.strip(),
                    Underline(Bold("Данный товар не будет учтён в инвентаризации")),
                    Bold("Данный товар не относится к выбранной товарной группе"),
                    as_line(Underline("Название:"), Code(cis.name), sep=" ", end=""),
                    as_line(
                        Underline("Штрихкод:"),
                        Code(get_ean_from_gtin(cis.gtin)),
                        sep=" ",
                        end="",
                    ),
                    as_line(
                        Underline("Маркировка:"), Code(Code(cis.cis)), sep=" ", end=""
                    ),
                    sep="\n",
                )
                log_m.debug(
                    f"Не соотвествует товарной группе {cis.pg_name} !={inventory_pg_name}"
                )
                await message.answer(**text.as_kwargs())
                await asyncio.sleep(1)
            else:
                correct_pg_name.append(cis)
        # Не числятся у вас на остатках
        pg_info = await get_pg_info(inventory_pg_name)
        if pg_info.is_volume_balance:
            skip_gtin = []
            for cis in correct_pg_name:
                if cis.gtin in skip_gtin:
                    continue
                current_gtins = [c for c in correct_pg_name if c.gtin == cis.gtin]
                if cis.gtin not in [p.gtin for p in inventory.products_balance]:
                    text = as_line(
                        texts.intersum_head.strip(),
                        Underline(
                            Bold("Данные товары не будет учтёны в инвентаризации")
                        ),
                        Bold("Данные товары не числятся у вас на остатках"),
                        as_line(
                            Underline("Количество:"),
                            Code(len(current_gtins)),
                            sep=" ",
                            end="",
                        ),
                        as_line(
                            Underline("Название:"), Code(cis.name), sep=" ", end=""
                        ),
                        as_line(
                            Underline("Штрихкод:"),
                            Code(get_ean_from_gtin(cis.gtin)),
                            sep=" ",
                            end="",
                        ),
                        as_line(
                            Underline("Маркировка:"),
                            Code(Code(cis.cis)),
                            sep=" ",
                            end="",
                        ),
                        sep="\n",
                    )
                    skip_gtin.append(cis.gtin)
                    log_m.debug(f"Товар не числится у вас на остатках")
                    await message.answer(**text.as_kwargs())
                    await asyncio.sleep(1)
                else:
                    result.append(cis)
        else:
            for cis in correct_pg_name:
                if cis.cis not in [
                    c.cis for p in inventory.products_balance for c in p.cises
                ]:
                    text = as_line(
                        texts.intersum_head.strip(),
                        Underline(Bold("Данный товар не будет учтён в инвентаризации")),
                        Bold("Данный товар не числится у вас на остатках"),
                        as_line(
                            Underline("Название:"), Code(cis.name), sep=" ", end=""
                        ),
                        as_line(
                            Underline("Штрихкод:"),
                            Code(get_ean_from_gtin(cis.gtin)),
                            sep=" ",
                            end="",
                        ),
                        as_line(
                            Underline("Маркировка:"),
                            Code(Code(cis.cis)),
                            sep=" ",
                            end="",
                        ),
                        sep="\n",
                    )
                    log_m.debug(f"Товар не числится у вас на остатках")
                    await message.answer(**text.as_kwargs())
                    await asyncio.sleep(1)
                else:
                    result.append(cis)

        return result
    except TelegramRetryAfter:
        await asyncio.sleep(3)


async def get_cises_from_message(
    message: Message, log_m, inventory: Inventory, znak: TrueApi, inventory_pg_name: str
) -> list[CIS]:
    if message.web_app_data is not None:

        def clean_and_decode(value):
            cleaned_value = value.replace("\x1d", "")
            if "\\u" in cleaned_value:
                decoded_value = cleaned_value.encode("utf-8").decode("unicode_escape")
            else:
                decoded_value = cleaned_value
            return decoded_value

        cises = [
            clean_and_decode(item) for item in json.loads(message.web_app_data.data)
        ]
        log_m.info(f'Отсканировал сканером марку(-и) "{cises}"')
    else:
        cises = message.text.split()
        log_m.info(f'Написали штрихкод(-а) "{cises}"')
    r_cises = [c.replace("(21)", "").replace("(01)", "") for c in cises]
    cises = await check_cises_errors(
        r_cises, inventory, message, znak, inventory_pg_name, log_m
    )
    return cises
