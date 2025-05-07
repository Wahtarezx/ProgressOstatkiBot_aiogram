#!/usr/bin/env python3.10
# -*- coding: utf-8 -*-

import asyncio
import os

import aiogram.exceptions
from aiogram import Dispatcher, F, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ContentType
from aiogram.filters import Command, ExceptionTypeFilter, CommandStart
from aiogram.fsm.storage.redis import RedisStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from pydantic import ValidationError

from core.cron.barcodes import update_all_in_sql
from core.cron.notification.start import send_notifications, create_notifications
from core.filters.iscontact import IsTrueContact
from core.handlers import basic, contact, errors_hand
from core.loggers.make_loggers import create_loggers
from core.middlewares.chat_action import ChatActionMiddleware
from core.middlewares.edo_middleware import EDOMessageMiddleware, EDOCallBackMiddleware
from core.middlewares.log_middles import (
    CallBackMiddleware,
    MessageMiddleware,
    ErrorEventMiddleware,
)
from core.notification.model import *
from core.services.admin.handlers.routers import routers as admin_routers
from core.services.cash_sales.handlers.routers import routers as cash_sales_routers
from core.services.edo.handlers.routers import edo_routers
from core.services.egais import inventory
from core.services.egais.TTN import list_ttns, resend, accept
from core.services.egais.auth import add as add_autologin
from core.services.egais.auth import auth as auth_autologin
from core.services.egais.auth import delete as delete_autologin
from core.services.egais.callbackdata import DelComp, ChangeComp
from core.services.egais.goods import (
    changePrice,
    generate_barcodes,
    create_barcodes,
    rozliv_alco,
)
from core.services.egais.logins import loginTTN, loginGoods, loginInventory
from core.services.egais.online_checks.routers import online_check_routers
from core.services.egais.states import RozlivAlcoState
from core.services.egais_ostatki.handlers.routers import (
    routers as egais_ostatki_routers,
)
from core.services.loyalty.handlers.routers import loyalty_routers
from core.services.markirovka.callbackdata import *
from core.services.markirovka.handlers import callback as mrk_callback
from core.services.markirovka.inventory import inventory as mrk_inventory
from core.services.markirovka.ostatki import actual as mrk_actual_ostatki
from core.services.markirovka.ostatki import date as mrk_date_ostatki
from core.services.markirovka.states import *
from core.services.markirovka.trueapi import ZnakAPIError
from core.services.profile.handlers.routers import routers as profile_routers
from core.services.provider_panel.handlers.routers import (
    routers as provider_panel_routers,
)
from core.utils.callbackdata import *
from core.utils.commands import set_default_commands, update_users_commands
from core.utils.edo_providers.edo_lite.model import EdoLiteError
from core.utils.states import *

from core.cron.barcodes import update_dcode_in_tmc

from config import ip


@logger.catch()
async def start():
    await create_loggers()
    bot = Bot(token=config.token, default=DefaultBotProperties(parse_mode="HTML"))
    if not config.develope_mode:
        await bot.send_message(5263751490, "Я Запустился!")
    if not config.develope_mode:
        await set_default_commands(bot)
        await update_users_commands(bot)
    # await set_developer_commands(bot)
    storage = RedisStorage.from_url(config.redisStorage)
    dp = Dispatcher(storage=storage)
    if os.name == "posix" and not config.develope_mode:
        scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
        scheduler.add_job(update_all_in_sql, trigger="interval", minutes=10)
        # scheduler.add_job(main_logs, trigger='cron', hour="*/5", minute="15")
        scheduler.add_job(send_notifications, trigger="cron", hour="15", minute="0")
        scheduler.add_job(create_notifications, trigger="cron", hour="13", minute="0")
        scheduler.add_job(update_dcode_in_tmc, trigger="cron", hour="5", minute="0", kwargs={"ip": ip})
        # scheduler.add_job(send_notification, trigger='cron', hour='*', minute='36')
        scheduler.start()


    # Errors handlers
    dp.errors.register(
        errors_hand.error_validationError, ExceptionTypeFilter(ValidationError)
    )
    dp.errors.register(
        errors_hand.error_tgBadRequest,
        ExceptionTypeFilter(aiogram.exceptions.TelegramBadRequest),
    )
    dp.errors.register(errors_hand.error_valueError, ExceptionTypeFilter(ValueError))
    dp.errors.register(
        errors_hand.error_ConnectionError, ExceptionTypeFilter(ConnectionError)
    )
    dp.errors.register(
        errors_hand.error_sqlalchemy,
        ExceptionTypeFilter(sqlalchemy.exc.OperationalError),
    )
    dp.errors.register(
        errors_hand.error_EDO, ExceptionTypeFilter(EdoLiteError, ZnakAPIError)
    )
    dp.errors.register(errors_hand.error_total, ExceptionTypeFilter(Exception))

    # Мидлвари
    dp.callback_query.middleware(ChatActionMiddleware())
    dp.callback_query.middleware(CallBackMiddleware())
    dp.callback_query.middleware(EDOCallBackMiddleware())
    dp.message.middleware(MessageMiddleware())
    dp.message.middleware(EDOMessageMiddleware())
    dp.errors.middleware(ErrorEventMiddleware())

    # Калбэки с прошлого бота для регистрации
    dp.callback_query.register(basic.from_oldBot, F.data == "cb_last_ostatki")
    dp.callback_query.register(basic.from_oldBot, F.data == "cb_list_ostatki")

    # COMMANDS
    dp.message.register(basic.ref, Command(commands=["ref"]))
    dp.message.register(basic.my_id, Command(commands=["id"]))
    dp.message.register(basic.clear, Command(commands=["clear"]))
    dp.message.register(
        basic.deeplink_start,
        CommandStart(deep_link=True),
        flags={"long_operation": "typing"},
    )
    dp.message.register(
        basic.get_start, Command(commands=["start"]), flags={"long_operation": "typing"}
    )
    dp.message.register(
        basic.cc, Command(commands=["comp"]), flags={"long_operation": "typing"}
    )
    dp.message.register(
        basic.url, Command(commands=["url"]), flags={"long_operation": "typing"}
    )
    dp.message.register(
        basic.test, Command(commands=["test"]), flags={"long_operation": "typing"}
    )

    dp.message.register(basic.url2, TestState.uuid, flags={"long_operation": "typing"})

    # /admin
    dp.include_routers(*admin_routers)

    dp.callback_query.register(basic.callback_get_start, F.data == "callback_get_start")
    # Создание реферальной ссылки
    dp.message.register(basic.ref_cashnumber, RefState.enter_cashNumber)

    # region Авторизация Артикс
    dp.message.register(basic.auth_cash_number, Auth.send_cash_number)
    dp.message.register(basic.auth_password, Auth.send_password)
    # Добавить компьютер в быструю авторизвацию
    dp.callback_query.register(add_autologin.start_add_comp, F.data == "artix_add_cash")
    # Удалить компьютер из быстрой авторизвации
    dp.callback_query.register(
        delete_autologin.start_delete, F.data == "artix_delete_cash"
    )
    dp.callback_query.register(delete_autologin.end_delete, DelComp.filter())
    dp.callback_query.register(delete_autologin.delete_all_save_comp, F.data == 'artix_delete_all_save_cash')
    # Поменяли компьютер
    dp.callback_query.register(auth_autologin.change_comp, ChangeComp.filter())

    # endregion

    # CONTACT REGISTRATION
    dp.message.register(contact.get_true_contact, F.contact, IsTrueContact())
    dp.message.register(contact.get_fake_contact, F.contact)

    # Остатки ЕГАИС
    dp.include_routers(*egais_ostatki_routers)

    # region Накладные
    dp.callback_query.register(loginTTN.choose_entity, F.data == "WayBills")
    # TTNS STATES
    dp.callback_query.register(
        loginTTN.menu, ChooseEntity.filter(), StateTTNs.choose_entity
    )
    # TTNS MENU
    dp.callback_query.register(
        accept.choose_accept_ttns,
        F.data == "accept_ttns",
        flags={"long_operation": "typing"},
    )
    dp.callback_query.register(resend.resend_start_menu, F.data == "resend_ttns")
    dp.callback_query.register(list_ttns.choose_list_ttns, F.data == "list_ttns")

    # TTNS ACCEPT
    dp.callback_query.register(
        accept.start_accept_ttns, AcceptTTN.filter(), flags={"long_operation": "typing"}
    )
    dp.message.register(
        accept.mediagroup_accept_ttns, StateTTNs.accept_ttn, F.media_group_id, F.photo
    )
    dp.message.register(accept.photo_accept_ttns, StateTTNs.accept_ttn, F.photo)
    dp.message.register(accept.document_accept_ttn, StateTTNs.accept_ttn, F.document)
    dp.message.register(
        accept.message_accept_ttns,
        StateTTNs.accept_ttn,
        F.content_type.in_([ContentType.WEB_APP_DATA, ContentType.TEXT]),
    )
    dp.callback_query.register(
        accept.send_accept_ttn,
        SendAcceptTTN.filter(),
        flags={"long_operation": "typing"},
    )
    # TTNS ACCEPT ALL
    dp.callback_query.register(
        accept.accept_all_ttns,
        F.data == "accept_all_ttns",
        flags={"long_operation": "typing"},
    )
    # TTNS DIVIRGENCE
    dp.callback_query.register(
        accept.choose_divirgence_ttn, F.data == "choose_divergence_ttn"
    )
    dp.callback_query.register(
        accept.send_divirgence_ttn, F.data == "send_divergence_ttn"
    )
    dp.callback_query.register(
        accept.back_to_accept_ttn, F.data == "cancel_divergence_ttn"
    )
    # TTNS LIST
    dp.callback_query.register(list_ttns.info_ttn, ListTTN.filter())
    dp.callback_query.register(
        accept.menu_back_ttns, F.data == "menu_ttns"
    )  # Кнопка "Назад"
    # TTN RESEND
    # TTN RESEND ALL
    dp.callback_query.register(
        resend.resend_all_ttns,
        F.data == "resend_all_ttn",
        flags={"long_operation": "typing"},
    )
    # TTN RESEND from text
    dp.callback_query.register(
        resend.start_resend_ttn_from_text, F.data == "enter_ttn_for_resend_ttn"
    )
    dp.message.register(
        resend.end_resend_ttn_from_text, ResendTTNfromText.enter_ttnEgais
    )
    # TTN RESEND from list
    dp.callback_query.register(resend.resend_simple_ttn, ResendTTN.filter())

    # endregion

    # region Товары
    dp.callback_query.register(loginGoods.menu_goods, F.data == "goods")

    # region Сгенерерировать штрихкод
    dp.callback_query.register(
        generate_barcodes.select_dcode, F.data == "generate_barcode"
    )
    dp.callback_query.register(
        generate_barcodes.select_measure, SelectDcode.filter(), GenerateBarcode.dcode
    )
    dp.callback_query.register(
        generate_barcodes.accept_measure,
        SelectMeasure.filter(),
        GenerateBarcode.measure,
    )
    dp.message.register(
        generate_barcodes.photo_barcode, GenerateBarcode.barcode, F.photo
    )
    dp.message.register(
        generate_barcodes.document_barcode, GenerateBarcode.barcode, F.document
    )
    dp.message.register(generate_barcodes.text_barcode, GenerateBarcode.barcode)
    dp.message.register(generate_barcodes.price, GenerateBarcode.price)
    dp.message.register(generate_barcodes.accept_name, GenerateBarcode.name)
    # endregion

    # region Добавить товар
    dp.callback_query.register(create_barcodes.start_add_bcode, F.data == "new_barcode")
    dp.callback_query.register(
        create_barcodes.select_is_touch,
        AddToTouchPanel.filter(),
        AddToCashBarcode.is_touch,
    )
    dp.callback_query.register(
        create_barcodes.after_select_main_actionpanel,
        ActionpanelGoods.filter(),
        AddToCashBarcode.is_touch,
    )
    dp.callback_query.register(
        create_barcodes.select_actionpanelitem,
        ActionPanelItem.filter(),
        AddToCashBarcode.is_touch,
    )
    dp.callback_query.register(
        create_barcodes.select_dcode, SelectDcode.filter(), AddToCashBarcode.dcode
    )
    dp.callback_query.register(
        create_barcodes.accept_measure, SelectMeasure.filter(), AddToCashBarcode.measure
    )
    dp.callback_query.register(
        create_barcodes.volume_draftbeer,
        VolumeDraftBeer.filter(),
        AddToCashBarcode.volume_draftbeer,
    )
    dp.message.register(
        create_barcodes.expirationdate_draftbeer,
        AddToCashBarcode.expirationdate_draftbeer,
    )
    dp.message.register(
        create_barcodes.photo_barcode, AddToCashBarcode.barcode, F.photo
    )
    dp.message.register(
        create_barcodes.document_barcode, AddToCashBarcode.barcode, F.document
    )
    dp.message.register(create_barcodes.one_text_barcode, AddToCashBarcode.barcode)
    dp.message.register(create_barcodes.price, AddToCashBarcode.price)
    dp.message.register(create_barcodes.accept_name, AddToCashBarcode.name)
    dp.callback_query.register(
        create_barcodes.addbcode_commit, F.data == "commit_addbcode"
    )
    dp.callback_query.register(
        create_barcodes.load_prepare_commit, F.data == "send_prepare_commit_addbcode"
    )
    # endregion

    # region Изменение цены
    dp.callback_query.register(changePrice.send_barcode, F.data == "new_price_barcode")
    dp.message.register(changePrice.photo_barcode, ChangePrice.barcode, F.photo)
    dp.message.register(changePrice.document_barcode, ChangePrice.barcode, F.document)
    dp.message.register(
        changePrice.text_barcode,
        ChangePrice.barcode,
        F.content_type.in_([ContentType.WEB_APP_DATA, ContentType.TEXT]),
    )
    dp.message.register(changePrice.final, ChangePrice.price)
    dp.callback_query.register(changePrice.send_barcode, F.data == "yes_again_price")
    dp.callback_query.register(basic.from_oldBot, F.data == "no_again_price")
    # endregion

    # region Разливной алкоголь
    dp.callback_query.register(rozliv_alco.start_scan_bcode, F.data == "rozliv_alco")
    dp.message.register(
        rozliv_alco.get_barcode,
        RozlivAlcoState.bcode,
        F.content_type.in_(
            [
                ContentType.PHOTO,
                ContentType.DOCUMENT,
                ContentType.WEB_APP_DATA,
                ContentType.TEXT,
            ]
        ),
    )
    dp.message.register(rozliv_alco.get_amark, RozlivAlcoState.amark)
    dp.message.register(rozliv_alco.volume, RozlivAlcoState.quantity)
    dp.callback_query.register(rozliv_alco.commit, F.data == "commit_rozliv_alco")
    dp.callback_query.register(
        rozliv_alco.load_prepare_commit, F.data == "load_rozliv_alco"
    )
    dp.callback_query.register(rozliv_alco.more_alco, F.data == "more_alco")
    # endregion

    # region Инвентаризация
    # логин
    dp.callback_query.register(loginInventory.menu, F.data == "inventory")
    dp.callback_query.register(inventory.start_inventory, F.data == "start_inventory")
    dp.message.register(inventory.message_inventory, Inventory_EGAIS.scaning)
    dp.callback_query.register(
        inventory.detailed_inventory, F.data == "detailed_invetory"
    )
    dp.callback_query.register(inventory.end_invetory, F.data == "end_invetory")
    # endregion

    # region Маркировка
    dp.include_routers(*edo_routers)

    # Меню
    dp.callback_query.register(
        mrk_callback.ostatki_menu, F.data == "markirovka_ostatki"
    )
    dp.callback_query.register(
        mrk_inventory.choice_product_group, F.data == "markirovka_inventory"
    )

    # region Инвентаризация
    # Выбрали товарную группу
    dp.callback_query.register(
        mrk_inventory.choise_action,
        ChoisePG.filter(),
        MarkirovkaMenu.inventory_choise_pg,
    )
    # Выбрали причину
    dp.callback_query.register(
        mrk_inventory.start_inventory,
        ChoiseAction.filter(),
        MarkirovkaMenu.inventory_choise_pg,
        flags={"long_operation": "upload_document"},
    )
    # Отсканировали товар
    dp.message.register(
        mrk_inventory.scanned_inventory,
        F.content_type.in_([ContentType.WEB_APP_DATA, ContentType.TEXT]),
        MarkirovkaMenu.inventory_start,
    )

    # Подробная информация об инвентаризации
    dp.callback_query.register(
        mrk_inventory.more_scanned_info, F.data == "chz_inventory_info"
    )
    # Перейти к заверешению
    dp.callback_query.register(
        mrk_inventory.confirm_inventory_end, F.data == "chz_inventory_confirm_end"
    )
    # Завершить сканирование
    dp.callback_query.register(
        mrk_inventory.end_inventory, F.data == "chz_inventory_end"
    )

    # endregion

    # region Остатки
    # region Актуальные
    dp.callback_query.register(
        mrk_actual_ostatki.start_actual, F.data == "ostatki_actual"
    )
    # Выбор товарной группы для получения
    dp.callback_query.register(
        mrk_actual_ostatki.choise_product_group,
        ChoisePG.filter(),
        MarkirovkaMenu.ostatki_actual,
    )
    # Выбрали все товарные группы
    dp.callback_query.register(
        mrk_actual_ostatki.select_all_product_groups, F.data == "ostatki_select_all"
    )
    # Отправка остатков
    dp.callback_query.register(
        mrk_actual_ostatki.send_select_actual_ostatki,
        F.data == "ostatki_actual_all",
        flags={"long_operation": "upload_document"},
    )
    # endregion
    # region Конкретная дата
    dp.callback_query.register(mrk_date_ostatki.date_ostatki, F.data == "ostatki_data")
    # endregion
    # endregion

    # endregion

    # Дегустация
    dp.include_routers(*online_check_routers)

    # Панель поставщика
    dp.include_routers(*provider_panel_routers)

    # Продажи
    dp.include_routers(*cash_sales_routers)

    # Информация о кассе
    dp.include_routers(*profile_routers)

    # Система лояльности
    dp.include_routers(*loyalty_routers)

    try:
        await dp.start_polling(bot, skip_updates=False)
    except aiogram.exceptions.TelegramNetworkError:
        dp.callback_query.register(basic.get_start)
    except Exception as e:
        logger.exception(e)
    finally:
        if not config.develope_mode:
            await bot.send_message(5263751490, "Я Остановился!!!!")
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(start())
