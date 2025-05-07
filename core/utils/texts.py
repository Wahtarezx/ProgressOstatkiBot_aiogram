import re
from datetime import datetime, timedelta
from typing import Tuple, List

from aiogram.utils.formatting import as_line, Bold, Underline, Text
from funcy import str_join

from core.services.markirovka.inventory.models import Inventory, InventoryExcel
from core.services.markirovka.ofdplatforma import get_pg_info
from core.utils.CS.pd_onlinecheck import Degustation
from core.utils.foreman.pd_model import ForemanCash


def phone(client_phone):
    client_phone = str_join(sep="", seq=re.findall(r"[0-9]*", client_phone))
    if re.findall(r"^89", client_phone):
        return re.sub(r"^89", "79", client_phone)
    return client_phone


def ostatki_date(date):
    return f"Остатки <b><u>{date}</u></b>\nЧтобы получить более свежие остатки, обратитесь к нам в тех.поддержку"


def accept_text(boxs) -> list[str]:
    result = []
    text = "➖➖➖<b><u>Позиции для приёма</u></b>➖➖➖\n"
    text += "Название | Обьем | Кол-во бутылок\n"
    text += "➖" * 15 + "\n"
    count = 0
    for box in boxs:
        if not box.scaned:
            text += f"{box.name} | {box.capacity[:4]}л | {box.count_bottles}шт\n"
        else:
            text += (
                f"<s>{box.name} | {box.capacity[:4]}л | {box.count_bottles}шт</s>✅\n"
            )
            count += 1
        if len(text) > 3800:
            result.append(text)
            text = ""
    text += "➖" * 15 + "\n"
    text += f"Принято <b><u>{count}</u></b> из <b><u>{len(boxs)}</u></b> позиций"
    result.append(text)
    return result


def divirgence_text(boxs):
    text = "<b><u>Ниже перечисленные коробки не будут потдверждены</u></b>\n"
    text += "Название | Обьем | Кол-во бутылок | Номер коробки\n"
    text += "➖" * 15 + "\n"
    for box in boxs:
        if not box.scaned:
            text += f"{box.name} | {box.capacity[:4]}л | {box.count_bottles}шт | {box.boxnumber}\n"
    text += "➖" * 15 + "\n"
    return text


def beer_accept_text(bottles):
    text = "➖➖➖<b><u>Бутылки для приёма</u></b>➖➖➖\n"
    text += "Название | Кол-во бутылок\n"
    text += "➖" * 15 + "\n"
    for bottle in bottles:
        text += f"{bottle.name} | {bottle.quantity}шт\n"
    return text


def scanning_inventory(bottles):
    text = "➖➖➖<b><u>Инвентаризация</u></b>➖➖➖\n"
    text += f"Отсканировано бутылок: <b><u>{len(bottles)}</u></b>\n"
    return text


def detailed_inventory(detailed_bottles):
    text = "➖➖➖<b><u>Инвентаризация</u></b>➖➖➖\n"
    text += "Название | Кол-во бутылок\n"
    text += "➖" * 15 + "\n"
    total = 0
    for bottle in detailed_bottles:
        text += f"{bottle.name} | <b><u>{bottle.count} шт</u></b>\n"
        text += "➖" * 10 + "\n"
        total += bottle.count
    text += f"Всего отсканировано: <b><u>{total} шт</u></b>\n"
    print(len(text))
    return text


async def error_message_wp(cash: ForemanCash, error: str):
    return (
        "Здравствуйте!\n"
        f"Это компьютер: {cash.shopcode}-{cash.cashcode}\n"
        f"У меня в телеграм боте вышли следующие ошибки, посмотрите пожалуйста.\n\n"
        f"{error}"
    )


error_head = f"➖➖➖➖🚨ОШИБКА🚨➖➖➖➖\n"
intersum_head = f"➖➖➖➖❗️ВАЖНО❗️➖➖➖➖\n"
information_head = f"➖➖➖ℹ️Информацияℹ️➖➖➖\n"
auth_head = f"➖➖➖🔑Авторизация🔑➖➖➖\n"
success_head = "➖➖➖✅УСПЕШНО✅➖➖➖\n"

develop = "Данная кнопка в разработке"
error_cashNumber = (
    error_head
    + f"Нужны только цифры. Например: <b><u>902</u></b>\n<b>Попробуйте снова</b>"
)
error_cashNotOnline = f"Компьютер не в сети. Возможно он выключен, или нет интернета."
error_fake_client_phone = error_head + f"Вы отправили чужой сотовый"
error_duplicateCash = (
    error_head
    + "С данным номером компьютера зарегистрировано больше одной кассы\nОбратитесь в тех поддрежку."
)
error_cash_not_found = (
    error_head + "Данная касса не найдена\nОбратитесь в тех поддрежку."
)
error_price_not_decimal = "{error_head}Цена содержит не нужные символы\nПопробуйте снова\nПример как надо: <u><b>10.12</b></u>".format(
    error_head=error_head
)
menu = (
    f"<u><b>Остатки</b></u> - Получить остатки магазина\n"
    f"<u><b>Накладные</b></u> - Операции с накладными\n"
    f"<u><b>Товары</b></u> - Операции с товарами\n"
    f"<u><b>Инвентаризация</b></u> - Выравнивание остатков\n",
    f"<u><b>Честный знак</b></u> - Операвции с Честным знаком\n",
    f"<u><b>Продажи</b></u> - Загрузка отчета по продажам\n",
)
menu_test = (
    f"<u><b>Остатки</b></u> - Получить остатки магазина\n"
    f"<u><b>Накладные</b></u> - Операции с накладными\n"
    f"<u><b>Товары</b></u> - Операции с товарами\n"
    f"<u><b>Инвентаризация</b></u> - Выравнивание остатков\n"
    f'<u><b>Честный знак</b></u> - Подтверждение, инвентаризация, остатки в СЭД "Честный знак"\n'
)
need_registration = (
    "Нужно пройти регистрацию в боте.\n"
    f'Нажмите на кнопку "Регистрация"\n'
    f'Если не видите кнопку "Регистрация", то посмотрите видео пример.'
)
succes_registration = "Регистрация успешно пройдена"
succes_inventory = "✅Инвентаризация успешно загружена✅\n"
WayBills = (
    f"<u><b>Подтвердить накладные</b></u> - Подтвердить не принятые накладные.\n"
    f"<u><b>Перевыслать накладные</b></u> - Повторная отправка накладной на кассу.\n"
    f"<u><b>Информация о последних накладных</b></u> - Выведем информацию о последних десяти накладных.\n"
)
WayBills_blacklist = (
    f"<u><b>Перевыслать накладные</b></u> - Повторная отправка накладной на кассу.\n"
    f"<u><b>Информация о последних накладных</b></u> - Выведем информацию о последних десяти накладных.\n"
)
resend_ttn = (
    "<b><u>Все не принятые ТТН</u></b> - Перевысылает ранее не принятые накладные\n"
    "<b><u>Выбрать из списка ТТН</u></b> - Выводит список из 10 последних поступавших к вам накладных\n"
    "<b><u>Ввести номер ТТН в ручную</u></b> - Вводите номер ТТН ЕГАИС в ручную\n"
)
goods = (
    f"<u><b>Сгенерерировать штрихкод</b></u> - Создать свой штрихкод\n"
    f"<u><b>Добавить товар</b></u> - Добавить товар на кассу\n"
    f"<u><b>Изменить цену</b></u> - Изменить цену товара на кассе\n"
)
ostatki = (
    f"<u><b>Последние остатки</b></u> - Получить последние сгенерированные остатки\n"
    f"<u><b>Список по датам</b></u> - Выведем даты последних 6 сгенерированных остатков"
)
enter_cash_number = (
    "Напишите номер компьютера:\nНужны только цифры. Например: <b><u>902</u></b>"
)
list_ostatki = "Выберите нужную дату остатков"
choose_entity = "Выберите нужное юр.лицо"
inventory = "Чтобы начать сканирование, нажмите на кнопку"
load_information = "Загрузка информации..."
scan_photo_or_text = "Пожалуйста, отсканируйте товарный штрихкод, отправьте фотографию, или напишите его вручную."
scan_datamatrix_photo = "Пожалуйста, отсканируйте маркировку, или отправьте фотографию."

markirovka_doc_menu = (
    f"<u><b>Подтвердить накладные</b></u> - Подтвердить не принятые накладные.\n"
    f"<u><b>Информация о последних накладных</b></u> - Выведем информацию о последних десяти накладных.\n"
)

markirovka_menu = (
    # f'<u><b>Остатки</b></u> - Получить остатки магазина\n'
    # f'<u><b>Инвентаризация</b></u> - Выравнивание остатков\n'
    f"<u><b>Накладные</b></u> - Операции с накладными\n"
    f"<u><b>Разливное пиво</b></u> - Поставить пиво на кран\n"
)

sub_to_tg_channel = (
    f"{intersum_head}"
    f"Для продолжения использования бота, пожалуйста, подпишитесь на наш канал в Телеграм: @egais116"
)
fail_to_wait_sub = (
    f"{error_head}"
    f"Время ожидания подписки на канал истекло.\n\n"
    f"Подпишитесь на канал @egais116 и повторите попытку."
)


def degustation(degustation: Degustation) -> list[Text]:
    text = as_line("➖" * 3, Underline(Bold("Дегустация")), "➖" * 3)
    for i, g in enumerate(degustation.goods):
        text += as_line()


def markirovka_inventory_info(
    inventory: Inventory, only_total_scanned: bool = True
) -> list[Text]:
    result = []
    text = as_line("➖" * 3, Underline(Bold("Инвентаризация")), "➖" * 3)
    if only_total_scanned:
        text += as_line(
            "Всего отсканировано: ",
            Underline(
                Bold(sum([p.gtin_quantity for p in inventory.products_inventory]))
            ),
            " шт",
        )
        result.append(text)
        return result
    else:
        total_scanned = 0
        for p in inventory.products_inventory:
            text += as_line(p.name, " | ", p.gtin, " | ", p.gtin_quantity, " шт")
            text += as_line("➖" * 10)
            total_scanned += p.gtin_quantity
            if len(text) > 3800:
                result.append(text)
                text = Text()
        text += as_line("Всего отсканировано: ", Underline(Bold(total_scanned)), " шт")
        result.append(text)
    return result


async def markirovka_inventory_confirm_info(inventory: InventoryExcel) -> str:
    text = (
        f"{information_head}"
        f"<b>Товарная группа:</b> <code>{(await get_pg_info(inventory.pg_name)).name}</code>\n"
        f"<b>Количество товара на списание:</b> <code>{inventory.count}</code> шт\n"
        f"<b>Количество позиций на списание:</b> <code>{inventory.count_positions}</code>\n"
    )
    return text


async def markirovka_inventory_more_info(inventory: InventoryExcel) -> str:
    text = (
        f"{information_head}"
        f"<b>Товарная группа:</b> <code>{(await get_pg_info(inventory.pg_name)).name}</code>\n"
        f"<b>Отсканированных товаров:</b> <code>{inventory.count}</code> шт\n"
        f"<b>Отсканировано позиций:</b> <code>{inventory.count_positions}</code>\n"
    )
    return text

    # result = []
    # text = as_line('➖' * 3, Underline(Bold('Инвентаризация')), '➖' * 3)
    # if only_total_scanned:
    #     text += f'Будет списано: <b><u>{sum([p.gtin_quantity for p in inventory.products_inventory])}</u></b> шт'
    # else:
    #     text += as_line(Underline("Список товаров на списание"))
    #     text += as_line(Bold("Название", " | ", "Количество"))
    #     text += as_line("➖" * 10)
    #     total_scanned = 0
    #     for p_b in inventory.products_balance:
    #         find = False
    #         for p in inventory.products_inventory:
    #             if p_b.gtin == p.gtin:
    #                 current_quantiy = p_b.gtin_quantity - p.gtin_quantity
    #                 if current_quantiy == 0:
    #                     continue
    #                 text += as_line(p_b.name, ' | ',  current_quantiy,  ' шт')
    #                 text += as_line("➖" * 10)
    #                 total_scanned += current_quantiy
    #                 find = True
    #                 break
    #         if not find:
    #             text += as_line(p_b.name, ' | ', p_b.gtin_quantity, ' шт')
    #             text += as_line("➖" * 10)
    #             total_scanned += p_b.gtin_quantity
    #         if len(text) > 3800:
    #             result.append(text)
    #             text = Text()
    #
    #     text += as_line('Будет списано: ', Underline(Bold(total_scanned)), ' шт')
    #     result.append(text)
    # return result


async def profile(cash: ForemanCash) -> Tuple[str, List[str]]:
    """
    Формирует текстовый отчёт о состоянии кассы и список ошибок.

    :param cash: Объект ForemanCash с информацией о кассе.
    :return: Кортеж из полного текста отчёта и списка ошибок.
    """
    info_lines = [information_head]
    error_messages = []

    def add_info(message: str):
        info_lines.append(message)

    def add_error(message: str):
        error_messages.append(f"❌{message}")
        info_lines.append(f"❌{message}")  # Включаем ошибки в общий текст

    # Проверка версии артикс
    try:
        version_patch = int(cash.artix_version.split(".")[2])
        if version_patch >= 253:
            add_info("<b>Версия программы</b>: Соответствует ✅\n")
        else:
            add_error("<b>Нужно обновить версию программы</b>\n")
    except (IndexError, ValueError):
        add_error("<b>Версия программы</b>: Некорректный формат версии\n")

    # Добавление основной информации
    add_info(f"<b>Номер компьютера:</b> <code>{cash.shopcode}</code>\n")
    add_info(f"<b>Номер кассы:</b> <code>{cash.cashcode}</code>\n")
    add_info(f"<b>Адрес:</b> <code>{cash.address}</code>\n")
    add_info(f"<b>ИНН:</b> <code>{cash.inn}</code>\n")

    if cash.kpp:
        add_info(f"<b>КПП:</b> <code>{cash.kpp}</code>\n")

    # Проверка токена
    if cash.xapikey:
        add_info(f"<b>Токен:</b> <code>{cash.xapikey}</code>\n")
    else:
        if cash.kkm2_number and float(cash.kkm2_ffd_version) == 1.2:
            add_error("<b><u>Нужно добавить токен разрешительного режима</u></b>️\n")

    # Проверка чековых аппаратов
    if (cash.kkm1_number and cash.kkm1_fn_number) or (
        cash.kkm2_number and cash.kkm2_fn_number
    ):
        add_info("ℹ️ Чековые аппараты ℹ️\n")
        # Проверка ККМ1
        if cash.kkm1_number and cash.kkm1_fn_number:
            add_info(f"#1 <b>{cash.kkm1_name}</b>\n")
            add_info(f"➖ <b>Заводской номер</b>: <code>{cash.kkm1_number}</code>\n")
            add_info(f"➖ <b>Номер ФН</b>: <code>{cash.kkm1_fn_number}</code>\n")
            add_info(f"➖ <b>Версия ФФД</b>: <code>{cash.kkm1_ffd_version}</code>\n")
            add_info(f"➖ <b>Версия прошивки</b>: <code>{cash.kkm1_firmware}</code>\n")
            add_info(f"➖ <b>НДС</b>: <code>{cash.kkm1_taxmapping}</code>\n")

            # Проверка срока действия ФН
            try:
                kkm1_fn_date = datetime.strptime(cash.kkm1_fn_date_end, "%d.%m.%Y")
                now = datetime.now()
                if now > kkm1_fn_date:
                    add_error("<b>Вышел срок действия ФН</b>\n")
                elif now - timedelta(days=7) > kkm1_fn_date:
                    add_error("<b>Выходит срок действия ФН</b>\n")
                add_info(
                    f"➖ <b>Дата окончания ФН</b>: <code>{cash.kkm1_fn_date_end}</code>\n"
                )
            except ValueError:
                add_error("<b>Дата окончания ФН</b>: Некорректный формат даты\n")

            # Проверка обновлений для ККМ1
            kkm1_need_update = []
            if cash.os_name == "bionic" and cash.kkm1_name == "АТОЛ":
                km_version = cash.kkm1_firmware.split(".")
                try:
                    major = int(km_version[0])
                    minor = int(km_version[1])
                    if major < 5:
                        kkm1_need_update.append(
                            "Нужно обновить версию прошивки до 5-ой версии"
                        )
                    if major == 5 and minor < 8:
                        kkm1_need_update.append(
                            "Минимальная версия прошивки должна быть минимум 5.8"
                        )
                except (IndexError, ValueError):
                    kkm1_need_update.append("Некорректный формат версии прошивки")

            # try:
            #     if float(cash.kkm1_ffd_version) < 1.2:
            #         kkm1_need_update.append('Минимальная версия ФФД должна быть минимум 1.2')
            # except ValueError:
            #     kkm1_need_update.append('Некорректный формат версии ФФД')

            if kkm1_need_update:
                add_info("  ⚠️<b><u>Нужно обновить</u></b>⚠️\n")
                for update_msg in kkm1_need_update:
                    add_error(f"{update_msg}\n")
            else:
                add_info("➖ <b>Состояние ФР</b>: Соответствует ✅\n")

        # Проверка ККМ2
        if cash.kkm2_number and cash.kkm2_fn_number:
            add_info(f"#2 <b>{cash.kkm2_name}</b>\n")
            add_info(f"➖ <b>Заводской номер</b>: <code>{cash.kkm2_number}</code>\n")
            add_info(f"➖ <b>Номер ФН</b>: <code>{cash.kkm2_fn_number}</code>\n")
            add_info(f"➖ <b>Версия ФФД</b>: <code>{cash.kkm2_ffd_version}</code>\n")
            add_info(f"➖ <b>Версия прошивки</b>: <code>{cash.kkm2_firmware}</code>\n")
            add_info(f"➖ <b>НДС</b>: <code>{cash.kkm2_taxmapping}</code>\n")

            # Проверка срока действия ФН
            try:
                kkm2_fn_date = datetime.strptime(cash.kkm2_fn_date_end, "%d.%m.%Y")
                now = datetime.now()
                if now > kkm2_fn_date:
                    add_error("<b>Вышел срок действия ФН</b>\n")
                elif now - timedelta(days=7) > kkm2_fn_date:
                    add_error("<b>Выходит срок действия ФН</b>\n")
                add_info(
                    f"➖ <b>Дата окончания ФН</b>: <code>{cash.kkm2_fn_date_end}</code>\n"
                )
            except ValueError:
                add_error("<b>Дата окончания ФН</b>: Некорректный формат даты\n")

            # Проверка обновлений для ККМ2
            kkm2_need_update = []
            if cash.os_name == "bionic" and cash.kkm2_name == "АТОЛ":
                km_version = cash.kkm2_firmware.split(".")
                try:
                    major = int(km_version[0])
                    minor = int(km_version[1])
                    if major < 5:
                        kkm2_need_update.append(
                            "Нужно обновить версию прошивки до 5-ой версии"
                        )
                    if major == 5 and minor < 8:
                        kkm2_need_update.append(
                            "Минимальная версия прошивки должна быть минимум 5.8"
                        )
                except (IndexError, ValueError):
                    kkm2_need_update.append("Некорректный формат версии прошивки")

            try:
                if float(cash.kkm2_ffd_version) < 1.2:
                    kkm2_need_update.append(
                        "Минимальная версия ФФД должна быть минимум 1.2"
                    )
            except ValueError:
                kkm2_need_update.append("Некорректный формат версии ФФД")

            if kkm2_need_update:
                add_info("  ⚠️<b><u>Нужно обновить</u></b>⚠️\n")
                for update_msg in kkm2_need_update:
                    add_error(f"{update_msg}\n")
            else:
                add_info("➖ <b>Состояние ФР</b>: Соответствует ✅\n")

    # Проверка Рутокенов
    if (cash.gost1_date_end and cash.pki1_date_end) or (
        cash.gost2_date_end and cash.pki2_date_end
    ):
        add_info("ℹ️ Рутокены ℹ️\n")
        # Проверка ГОСТ1 и PKI1
        if cash.gost1_date_end:
            add_info(f"#1 <b>{cash.artix_shopname}</b>\n")
            add_info(f"➖ <b>ФСРАР ID</b>: <code>{cash.fsrar}</code>\n")
            try:
                gost1_date = datetime.strptime(cash.gost1_date_end, "%Y-%m-%d")
                pki1_date = datetime.strptime(cash.pki1_date_end, "%Y-%m-%d")
                now = datetime.now()
                if now > gost1_date:
                    add_error(
                        f"<b>Вышел срок действия ГОСТ ООО Рутокена ({gost1_date})</b>\n"
                    )
                elif now - timedelta(days=7) > gost1_date:
                    add_error(
                        f"<b>Выходит срок действия ГОСТ ООО Рутокена ({gost1_date})</b>\n"
                    )
                add_info(
                    f"➖ <b>Дата окончания ГОСТ</b>: <code>{cash.gost1_date_end}</code>\n"
                )
            except ValueError:
                add_error("<b>Дата окончания ГОСТ</b>: Некорректный формат даты\n")

            try:
                if datetime.now() > pki1_date:
                    add_error(
                        f"<b>Вышел срок действия PKI ООО Рутокена ({pki1_date})</b>️\n"
                    )
                elif datetime.now() - timedelta(days=7) > pki1_date:
                    add_error(
                        "<b>Выходит срок действия PKI ООО Рутокена ({pki1_date})</b>\n"
                    )
                add_info(
                    f"➖ <b>Дата окончания PKI</b>: <code>{cash.pki1_date_end}</code>\n"
                )
            except (NameError, ValueError):
                add_error("<b>Дата окончания PKI</b>: Некорректный формат даты\n")

        # Проверка ГОСТ2 и PKI2
        if cash.gost2_date_end:
            add_info(f"#2 <b>{cash.artix_shopname2}</b>\n")
            add_info(f"➖ <b>ФСРАР ID</b>: <code>{cash.fsrar2}</code>\n")
            try:
                gost2_date = datetime.strptime(cash.gost2_date_end, "%Y-%m-%d")
                pki2_date = datetime.strptime(cash.pki2_date_end, "%Y-%m-%d")
                now = datetime.now()
                if now > gost2_date:
                    add_error(
                        f"<b>Вышел срок действия ГОСТ ИП Рутокена ({gost2_date})</b>\n"
                    )
                elif now - timedelta(days=7) > gost2_date:
                    add_error(
                        f"<b>Выходит срок действия ГОСТ ИП Рутокена ({gost2_date})</b>️\n"
                    )
                add_info(
                    f"➖ <b>Дата окончания ГОСТ</b>: <code>{cash.gost2_date_end}</code>\n"
                )
            except ValueError:
                add_error("<b>Дата окончания ГОСТ</b>: Некорректный формат даты\n")

            try:
                if datetime.now() > pki2_date:
                    add_error(f"<b>Вышел срок действия PKI ИП ({pki2_date})</b>\n")
                elif datetime.now() - timedelta(days=7) > pki2_date:
                    add_error(f"<b>Выходит срок действия PKI ИП ({pki2_date})</b>\n")
                add_info(
                    f"➖ <b>Дата окончания PKI</b>: <code>{cash.pki2_date_end}</code>\n"
                )
            except (NameError, ValueError):
                add_error("<b>Дата окончания PKI</b>: Некорректный формат даты\n")

    # Проверка списка кассиров
    if len(cash.list_mols) > 0:
        add_info("ℹ️ Кассиры ℹ️\n")
        if "Мастер" in cash.list_mols:
            add_error("<b>Вам нужно создать кассира с его ФИО</b>\n")
        for mol in [m for m in cash.list_mols if m != "Мастер"]:
            add_info(f"➖ <b>{mol}</b>\n")
    else:
        add_error("<b>Вам нужно создать кассира с его ФИО</b>\n")

    # Формирование итогового текста
    if len(error_messages) > 0:
        error_text = "⚠️<b><u>У вас есть следующие не соответствия</u></b>⚠️\n"
        error_text += "".join(error_messages)
        error_text += '\n<blockquote>Чтобы узнать более подробную информацию, нажмите кнопку "Информация о кассе"</blockquote>'
    else:
        error_text = ""

    full_text = "".join(info_lines)

    return full_text, error_text


no_sales = f"{error_head}У вас отсутствуют продажи"
