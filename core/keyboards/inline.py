import json
import urllib.parse as urlencode_text
from collections import namedtuple
from typing import Type

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from core.database.artix.model import Valut
from core.database.artix.querys import ArtixCashDB
from core.database.modelBOT import Clients
from core.database.models_enum import Roles
from core.database.query_BOT import check_cash_in_acceptlist, Database
from core.services.egais.callbackdata import *
from core.services.egais.goods.pd_models import Dcode, TmcType, OpMode, Measure
from core.services.markirovka.callbackdata import (
    AddToTouchPanel,
    ActionpanelGoods,
    ActionPanelItem,
    OnlineCheckTTN,
    cbValut,
    OnlineCheckTTNPage,
    OnlineCheckTTNDcode,
)
from core.utils.callbackdata import *
from core.utils.documents.pd_model import WB4
from core.utils.foreman.pd_model import ForemanCash

db = Database()


def kb_cb_startMenu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Главное меню", callback_data="callback_get_start")
    kb.adjust(2, repeat=True)
    return kb.as_markup()


def kb_startMenu(cash: ForemanCash, add_cash_info: bool = True):
    kb = InlineKeyboardBuilder()
    inline_kb_list = []
    if add_cash_info:
        inline_kb_list.append(
            [InlineKeyboardButton(text="Информация о кассе", callback_data="profile")]
        )
    inline_kb_list.append(
        [InlineKeyboardButton(text="Честный знак", callback_data="markirovka")]
    )
    inline_kb_list.append(
        [
            InlineKeyboardButton(text="Остатки", callback_data="ostatki"),
            InlineKeyboardButton(text="Накладные", callback_data="WayBills"),
        ]
    )
    inline_kb_list.append(
        [
            InlineKeyboardButton(text="Товары", callback_data="goods"),
            InlineKeyboardButton(text="Инвентаризация", callback_data="inventory"),
        ]
    )
    inline_kb_list.append(
        [
            InlineKeyboardButton(text="Продажи", callback_data="cash_sales"),
        ]
    )
    if cash.shopcode in [1978, 1306]:
        inline_kb_list.append(
            [
                InlineKeyboardButton(
                    text="Система лояльности", callback_data="loyalty_system"
                ),
            ]
        )
    if (
            cash.shopcode in [1519, 1306]
            or config.develope_mode
            or cash.artix_shopname.lower() == "biohacking"
    ):
        inline_kb_list.append(
            [InlineKeyboardButton(text="Онлайн чеки", callback_data="online_checks")]
        )
    # kb(text="Остатки", callback_data='ostatki')
    # kb.button(text="Накладные", callback_data='WayBills')
    # kb.button(text="Товары", callback_data='goods')
    # kb.button(text="Инвентаризация", callback_data='inventory')
    # kb.button(text="Честный знак", callback_data='markirovka')
    # if (cash.shopcode in [1519, 1306]
    #         or config.develope_mode
    #         or cash.artix_shopname.lower() == 'biohacking'):
    #     kb.button(text="Онлайн чеки", callback_data='online_checks')
    # kb.button(text="Продажи", callback_data='cash_sales')
    # kb.adjust(2, repeat=True)
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)


def kb_online_checks(cash: ForemanCash):
    kb = InlineKeyboardBuilder()
    if cash.artix_shopname.lower() == "biohacking" or config.develope_mode:
        kb.button(text="Сформировать чек", callback_data="online_check_basic")
    if cash.shopcode in [1519, 1306] or config.develope_mode:
        kb.button(text="Алкогольные накладные", callback_data="online_check_ttn")
        kb.button(text="Дегустация ", callback_data="online_check_degustation")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_onlinecheck_add_good() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="Добавить товар", callback_data="new_barcode")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_online_check_select_ttn(wbs4: list[WB4], page: int = 1):
    kb = InlineKeyboardBuilder()
    for wb in wbs4:
        kb.button(
            text=f"{wb.ttn_info.number} | {wb.ttn_info.ttn_date}",
            callback_data=OnlineCheckTTN(ttn_e=wb.file_path.parent.name),
        )
    if page > 1:
        kb.button(text=f"⬅️ Назад", callback_data=OnlineCheckTTNPage(page=page - 1))
        if wbs4:
            kb.button(text=f"➡️", callback_data=OnlineCheckTTNPage(page=page + 1))
    else:
        kb.button(text=f"➡️", callback_data=OnlineCheckTTNPage(page=page + 1))
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_online_check_with_check():
    kb = InlineKeyboardBuilder()
    kb.button(text="Продолжить", callback_data="continue_oc_ttn")
    kb.button(text="Добавить наценку на товар", callback_data="overprice_oc_ttn")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_select_procent_overprice():
    kb = InlineKeyboardBuilder()
    kb.button(text="5%", callback_data=OverpriceTTN(procent=5))
    kb.button(text="10%", callback_data=OverpriceTTN(procent=10))
    kb.button(text="15%", callback_data=OverpriceTTN(procent=15))
    kb.button(text="Напечатать самому", callback_data="enter_overprice_ttn")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_onlinecheck_ttn_ofd(ofd_dcode: Dcode):
    kb = InlineKeyboardBuilder()
    kb.button(text="С ОФД✅", callback_data=OnlineCheckTTNDcode(dcode=ofd_dcode.value))
    kb.button(
        text="Без ОФД❌", callback_data=OnlineCheckTTNDcode(dcode=Dcode.dummy.value)
    )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_valutes(valutes: list[Type[Valut]]):
    kb = InlineKeyboardBuilder()
    for valute in valutes:
        kb.button(text=valute.name, callback_data=cbValut(code=valute.code))
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_inventory():
    kb = InlineKeyboardBuilder()
    kb.button(text="Начать сканирование", callback_data="start_inventory")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_end_inventory():
    kb = InlineKeyboardBuilder()
    kb.button(text="Подробная информация о бутылках", callback_data="detailed_invetory")
    kb.button(text="Завершить сканирование", callback_data="end_invetory")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_detailed_inventory():
    kb = InlineKeyboardBuilder()
    kb.button(text="Завершить сканирование", callback_data="end_invetory")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_goods(cash: ForemanCash):
    kb = InlineKeyboardBuilder()
    kb.button(text="Сгенерерировать штрихкод", callback_data="generate_barcode")
    kb.button(text="Изменить цену", callback_data="new_price_barcode")
    kb.button(text="Добавить товар", callback_data="new_barcode")
    if cash.is_bar:
        kb.button(text="Разливной алкоголь", callback_data="rozliv_alco")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_genbcode_select_dcode():
    kb = InlineKeyboardBuilder()
    kb.button(
        text="Алкоголь",
        callback_data=SelectDcode(dcode="1", op_mode="192", tmctype="1"),
    )
    kb.button(
        text="Пиво", callback_data=SelectDcode(dcode="2", op_mode="64", tmctype="0")
    )
    kb.button(
        text="Сигареты",
        callback_data=SelectDcode(dcode="3", op_mode="32768", tmctype="3"),
    )
    kb.button(
        text="Продукты", callback_data=SelectDcode(dcode="4", op_mode="0", tmctype="0")
    )
    kb.button(
        text="Маркированный товар",
        callback_data=SelectDcode(dcode="5", op_mode="0", tmctype="7"),
    )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_addbcode_select_dcode():
    kb = InlineKeyboardBuilder()
    kb.button(
        text="Алкоголь",
        callback_data=SelectDcode(
            dcode=Dcode.alcohol, op_mode=OpMode.alcohol, tmctype=TmcType.alcohol
        ),
    )
    kb.button(
        text="Пиво",
        callback_data=SelectDcode(
            dcode=Dcode.beer,
            op_mode=OpMode.beer,
            tmctype=TmcType.basic,
        ),
    )
    kb.button(
        text="Сигареты",
        callback_data=SelectDcode(
            dcode=Dcode.tobacco,
            op_mode=OpMode.tobacco,
            tmctype=TmcType.tobacco,
        ),
    )
    kb.button(
        text="Продукты",
        callback_data=SelectDcode(
            dcode=Dcode.basic,
            op_mode=OpMode.basic,
            tmctype=TmcType.basic,
        ),
    )
    kb.button(
        text="Маркированный товар",
        callback_data=SelectDcode(
            dcode=Dcode.markirovka,
            op_mode=OpMode.basic,
            tmctype=TmcType.markedgoods,
        ),
    )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_addbcode_volume_draftbeer():
    kb = InlineKeyboardBuilder()
    for volume in [20, 30, 50]:
        kb.button(text=str(volume), callback_data=VolumeDraftBeer(volume=volume))
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_genbcode_select_measure_alcohol():
    kb = InlineKeyboardBuilder()
    kb.button(
        text="Поштучный",
        callback_data=SelectMeasure(
            measure=Measure.unit,
            op_mode=OpMode.alcohol,
            tmctype=TmcType.alcohol,
            qdefault=1,
        ),
    )
    kb.button(
        text="Розлив",
        callback_data=SelectMeasure(
            measure=Measure.unit,
            op_mode=OpMode.basic,
            tmctype=TmcType.basic,
            qdefault=1,
        ),
    )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_genbcode_select_measure_beer():
    kb = InlineKeyboardBuilder()
    kb.button(
        text="Поштучный",
        callback_data=SelectMeasure(
            measure=Measure.unit,
            op_mode=OpMode.beer,
            tmctype=TmcType.markedgoods,
            qdefault=1,
        ),
    )
    kb.button(
        text="Розлив",
        callback_data=SelectMeasure(
            measure=Measure.kg,
            op_mode=OpMode.beer,
            tmctype=TmcType.draftbeer,
            qdefault=0,
        ),
    )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_addbcode_select_measure_beer():
    kb = InlineKeyboardBuilder()
    kb.button(
        text="Поштучный",
        callback_data=SelectMeasure(
            measure=Measure.unit,
            op_mode=OpMode.beer,
            tmctype=TmcType.markedgoods,
            qdefault=1,
        ),
    )
    kb.button(
        text="Розлив",
        callback_data=SelectMeasure(
            measure=Measure.litr,
            op_mode=OpMode.beer,
            tmctype=TmcType.draftbeer,
            qdefault=0,
        ),
    )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_addbcode_select_measure_products():
    kb = InlineKeyboardBuilder()
    kb.button(
        text="Поштучный",
        callback_data=SelectMeasure(
            measure=Measure.unit,
            op_mode=OpMode.basic,
            tmctype=TmcType.basic,
            qdefault=1,
        ),
    )
    kb.button(
        text="Весовой",
        callback_data=SelectMeasure(
            measure=Measure.kg,
            op_mode=OpMode.basic,
            tmctype=TmcType.basic,
            qdefault=0,
        ),
    )
    kb.button(
        text="Розлив",
        callback_data=SelectMeasure(
            measure=Measure.litr,
            op_mode=OpMode.basic,
            tmctype=TmcType.basic,
            qdefault=0,
        ),
    )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_genbcode_select_measure_products():
    kb = InlineKeyboardBuilder()
    kb.button(
        text="Поштучный",
        callback_data=SelectMeasure(
            measure=Measure.unit,
            op_mode=OpMode.basic,
            tmctype=TmcType.basic,
            qdefault=1,
        ),
    )
    kb.button(
        text="Весовой",
        callback_data=SelectMeasure(
            measure=Measure.kg,
            op_mode=OpMode.basic,
            tmctype=TmcType.basic,
            qdefault=0,
        ),
    )
    kb.button(
        text="Розлив",
        callback_data=SelectMeasure(
            measure=Measure.litr,
            op_mode=OpMode.basic,
            tmctype=TmcType.basic,
            qdefault=0,
        ),
    )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_addbcode_prepare_commit():
    kb = InlineKeyboardBuilder()
    kb.button(text="Добавить еще товар ➕", callback_data="new_barcode")
    kb.button(text="Готово ✅", callback_data="commit_addbcode")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_addbcode_load_prepare_commit():
    kb = InlineKeyboardBuilder()
    kb.button(
        text="Список сканированных товаров ⏳",
        callback_data="send_prepare_commit_addbcode",
    )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_draftbeer_add_prepare_commit():
    kb = InlineKeyboardBuilder()
    kb.button(text="Добавить еще ➕", callback_data="more_draftbeer_add")
    kb.button(text="Готово ✅", callback_data="commit_draftbeer_add")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_draftbeer_add_load_prepare_commit():
    kb = InlineKeyboardBuilder()
    kb.button(
        text="Список ранее сканированных кег ⏳", callback_data="send_prepare_commit"
    )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_menu_ttns():
    kb = InlineKeyboardBuilder()
    kb.button(text="Подтвердить накладные", callback_data="accept_ttns")
    kb.button(text="Перевыслать накладные", callback_data="resend_ttns")
    kb.button(text="Информация о последних накладных", callback_data="list_ttns")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_menu_resend_ttns():
    kb = InlineKeyboardBuilder()
    kb.button(text="Все не принятые ТТН", callback_data="resend_all_ttn")
    kb.button(text="Выбрать из списка ТТН", callback_data="list_ttns")
    kb.button(
        text="Ввести номер ТТН в ручную", callback_data="enter_ttn_for_resend_ttn"
    )
    kb.button(text=f"⬅️ Назад", callback_data="menu_ttns")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_menu_ttns_who_in_blacklist():
    kb = InlineKeyboardBuilder()
    kb.button(text="Перевыслать накладные", callback_data="resend_ttns")
    kb.button(text="Информация о последних накладных", callback_data="list_ttns")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_whatsapp_url(
        message: str = "", button_text: str = "Тех.Поддержка", phone: str = "79600484366"
):
    kb = InlineKeyboardBuilder()
    if message:
        text = urlencode_text.quote(message)
        kb.button(text=button_text, url=f"wa.me/{phone}?text={text}")
    else:
        kb.button(text=button_text, url=f"wa.me/{phone}")
    kb.adjust(1)
    return kb.as_markup()


def kb_entity(cash: ForemanCash, UTM_8082: bool, UTM_18082: bool):
    kb = InlineKeyboardBuilder()
    if cash.artix_shopname and cash.fsrar and UTM_8082:
        kb.button(
            text=cash.artix_shopname,
            callback_data=ChooseEntity(
                inn=cash.inn,
                fsrar=cash.fsrar,
                port="8082",
                ip=cash.ip(),
            ),
        )
    if cash.artix_shopname2 and cash.fsrar2 and UTM_18082:
        kb.button(
            text=cash.artix_shopname2,
            callback_data=ChooseEntity(
                inn=cash.inn2,
                fsrar=cash.fsrar2,
                port="18082",
                ip=cash.ip(),
            ),
        )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_entity_offline(cash_info):
    kb = InlineKeyboardBuilder()
    try:
        ooo_inn, ooo_name, ooo_fsrar = (
            cash_info.inn,
            cash_info.ooo_name,
            cash_info.fsrar,
        )
    except AttributeError:
        ooo_inn, ooo_name, ooo_fsrar = False, False, False
    try:
        ip_inn, ip_name, ip_fsrar = (
            cash_info.ip_inn,
            cash_info.ip_name,
            cash_info.fsrar2,
        )
    except AttributeError:
        ip_inn, ip_name, ip_fsrar = False, False, False
    if ooo_inn and ooo_fsrar:
        kb.button(
            text=ooo_name,
            callback_data=ChooseEntity(
                inn=ooo_inn, fsrar=ooo_fsrar, port="8082", ip=cash_info.ip
            ),
        )
    if ip_inn and ip_fsrar:
        kb.button(
            text=ip_name,
            callback_data=ChooseEntity(
                inn=ip_inn, fsrar=ip_fsrar, port="18082", ip=cash_info.ip
            ),
        )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


async def kb_choose_ttn(TTNs: list, cash: ForemanCash, client: Clients):
    kb = InlineKeyboardBuilder()
    autoaccept_cash = await check_cash_in_acceptlist(
        f"cash-{cash.shopcode}-{cash.cashcode}"
    )
    role = Roles(client.role.role)
    for ttn in TTNs:
        kb.button(
            text=f"{ttn.date} | {ttn.wbnumber} | {ttn.shipper_name}",
            callback_data=AcceptTTN(
                id_f2r=ttn.id_f2r,
                id_wb=ttn.id_wb,
                ttn=ttn.ttn_egais,
                inn=ttn.shipper_inn,
            ),
        )
    if (
            role in [Roles.ADMIN, Roles.TEHPOD]
            or role == Roles.SAMAN_PROVIDER
            and cash.inn in config.SAMAN_INNS
            or role == Roles.PREMIER_PROVIDER
            and cash.inn in config.PREMIER_INNS
            or role == Roles.ROSSICH_PROVIDER
            and cash.inn in config.ROSSICH_INNS
    ):
        kb.button(text="Подтвердить все накладные✅", callback_data="accept_all_ttns")
    elif autoaccept_cash is not None:
        if autoaccept_cash.accept_all_inn:
            kb.button(
                text="Подтвердить все накладные✅", callback_data="accept_all_ttns"
            )

    kb.adjust(1, repeat=True)
    return kb.as_markup()


async def kb_accept_ttn(data: dict):
    def get_boxs(boxs):
        boxinfo = namedtuple(
            "Box", "identity name capacity boxnumber count_bottles amarks scaned"
        )
        result = []
        for identity, name, capacity, boxnumber, count_bottles, amarks, scaned in boxs:
            result.append(
                boxinfo(
                    identity, name, capacity, boxnumber, count_bottles, amarks, scaned
                )
            )
        return result

    kb = InlineKeyboardBuilder()
    boxs = get_boxs(data.get("boxs"))
    id_f2r = data.get("id_f2r")
    id_wb = data.get("id_wb")
    ttn_egais = data.get("ttn_egais")
    client = await db.get_client_info(data.get("user_id"))
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    scaned = all((box.scaned for box in boxs))
    count_accept_box = len([box for box in boxs if box.scaned])
    cash_auto_accept = await check_cash_in_acceptlist(
        f"cash-{cash.shopcode}-{cash.cashcode}"
    )
    shipper_inn = data.get("shipper_inn")
    role = Roles(client.role.role)

    if scaned:
        kb.button(
            text="Подтвердить накладную✅",
            callback_data=SendAcceptTTN(
                id_f2r=id_f2r, id_wb=id_wb, ttn=ttn_egais, alco=True, auto=False
            ),
        )
    elif (
            role in [Roles.ADMIN, Roles.TEHPOD]
            or role == Roles.SAMAN_PROVIDER
            and cash.inn in config.SAMAN_INNS
            or role == Roles.PREMIER_PROVIDER
            and cash.inn in config.PREMIER_INNS
            or role == Roles.ROSSICH_PROVIDER
            and cash.inn in config.ROSSICH_INNS
    ) and not scaned:
        kb.button(
            text="Подтвердить накладную✅",
            callback_data=SendAcceptTTN(
                id_f2r=id_f2r, id_wb=id_wb, ttn=ttn_egais, alco=True, auto=True
            ),
        )
        if count_accept_box > 0:
            kb.button(
                text="Отправить акт расхождения", callback_data="choose_divergence_ttn"
            )
    # Если номер компа есть в списке на приём без сканирования
    elif cash_auto_accept is not None:
        may_accept = (
            json.loads(cash_auto_accept.may_accept_inn)
            if cash_auto_accept.may_accept_inn
            else []
        )
        if (
                cash_auto_accept.accept_all_inn
                or (shipper_inn in may_accept)
                or (
                role in [Roles.ADMIN, Roles.TEHPOD]
                or role == Roles.SAMAN_PROVIDER
                and cash.inn in config.SAMAN_INNS
                or role == Roles.PREMIER_PROVIDER
                and cash.inn in config.PREMIER_INNS
                or role == Roles.ROSSICH_PROVIDER
                and cash.inn in config.ROSSICH_INNS
        )
        ):
            kb.button(
                text="Подтвердить накладную✅",
                callback_data=SendAcceptTTN(
                    id_f2r=id_f2r, id_wb=id_wb, ttn=ttn_egais, alco=True, auto=True
                ),
            )
        if count_accept_box > 0:
            kb.button(
                text="Отправить акт расхождения", callback_data="choose_divergence_ttn"
            )
    else:
        if count_accept_box > 0:
            kb.button(
                text="Отправить акт расхождения", callback_data="choose_divergence_ttn"
            )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_accept_beer_ttn(state_info):
    kb = InlineKeyboardBuilder()
    id_f2r = state_info.get("id_f2r")
    id_wb = state_info.get("id_wb")
    ttn_egais = state_info.get("ttn_egais")
    kb.button(
        text="Принять накладную",
        callback_data=SendAcceptTTN(
            id_f2r=id_f2r, id_wb=id_wb, ttn=ttn_egais, auto=False, alco=False
        ),
    )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_choose_divirgence_ttn():
    kb = InlineKeyboardBuilder()
    kb.button(text="Да", callback_data="send_divergence_ttn")
    kb.button(text="Нет", callback_data="cancel_divergence_ttn")
    kb.adjust(2, repeat=True)
    return kb.as_markup()


def kb_choose_list_ttn(ttns_info, ttnload):
    """
    :param ttns_info: list
    Список [date_ttn, wbnumber, shipper_name, ttn_egais]
    :param ttnload: str
    Название папки
    :return: Keyboard
    """
    kb = InlineKeyboardBuilder()
    for date_ttn, wbnumber, shipper_name, ttn_egais in ttns_info:
        kb.button(
            text=f"{date_ttn} | {wbnumber} | {shipper_name}",
            callback_data=ListTTN(ttnload=ttnload, ttn_e=ttn_egais),
        )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_info_ttn(status, ttn_egais, shipper_inn):
    kb = InlineKeyboardBuilder()
    if status == "ожидает":
        kb.button(text=f"Перейти к приёму", callback_data="accept_ttns")
    else:
        kb.button(
            text=f"Перевыслать ТТН",
            callback_data=ResendTTN(ttn_egais=ttn_egais, shipper_inn=shipper_inn),
        )
    kb.button(text=f"⬅️ Назад", callback_data="menu_ttns")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_info_ttn_in_blacklist(ttn_egais, shipper_inn):
    kb = InlineKeyboardBuilder()
    kb.button(
        text=f"Перевыслать ТТН",
        callback_data=ResendTTN(ttn_egais=ttn_egais, shipper_inn=shipper_inn),
    )
    kb.button(text=f"⬅️ Назад", callback_data="menu_ttns")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_add_to_touch():
    kb = InlineKeyboardBuilder()
    kb.button(text="Да", callback_data=AddToTouchPanel(touch=True))
    kb.button(text="Нет", callback_data=AddToTouchPanel(touch=False))
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_main_actionpanel_goods(cash: ForemanCash):
    kb = InlineKeyboardBuilder()
    artix = ArtixCashDB(ip=cash.ip())
    for (
            actionpanel,
            actionpanelitem,
            actionpanelparameter,
    ) in artix.get_main_actiopanelitems():
        if actionpanelparameter.parametername != "hotKeyCode":
            kb.button(
                text=f"{actionpanelitem.name} 🗂",
                callback_data=ActionpanelGoods(
                    acitem_id=actionpanelitem.actionpanelitemcode,
                    dir=True,
                    page=actionpanelparameter.parametervalue,
                    ctx=actionpanel.context,
                    act_par_code=actionpanelparameter.actionparametercode,
                ),
            )
        else:
            hotkey = artix.get_hotkey(actionpanelparameter.parametervalue)
            hotkey_items = artix.get_hotkeyinvents(hotkey.hotkeycode)
            kb.button(
                text=f"{actionpanelitem.name}📙",
                callback_data=ActionpanelGoods(
                    acitem_id=actionpanelitem.actionpanelitemcode,
                    dir=False,
                    hotkeycode=hotkey.hotkeycode,
                    hk_list=(
                        len(hotkey_items) > 1 if hotkey_items is not None else False
                    ),
                    page=0,
                    ctx=actionpanel.context,
                    act_par_code=actionpanelparameter.actionparametercode,
                ),
            )
    kb.adjust(3, repeat=True)
    return kb.as_markup()


def kb_select_actionitem(current_panel: ActionpanelGoods, cash: ForemanCash):
    kb = InlineKeyboardBuilder()
    artix = ArtixCashDB(cash.ip())
    apanel = artix.get_actionpanel_by_context_and_page(
        context=current_panel.ctx,
        page=current_panel.page,
    )
    panel_items = artix.get_actionpanelitems(
        apanel.actionpanelcode, apanel.context, apanel.page
    )
    for actionpanel, actionpanelitem, actionpanelparameter in panel_items:
        if actionpanelparameter.parametername != "hotKeyCode":
            kb.button(
                text=f"{actionpanelitem.name} 🗂",
                callback_data=ActionpanelGoods(
                    acitem_id=actionpanelitem.actionpanelitemcode,
                    dir=True,
                    page=actionpanelparameter.parametervalue,
                    ctx=actionpanel.context,
                    act_par_code=actionpanelparameter.actionparametercode,
                ),
            )
        else:
            hotkey = artix.get_hotkey(actionpanelparameter.parametervalue)
            hotkey_items = artix.get_hotkeyinvents(hotkey.hotkeycode)
            kb.button(
                text=actionpanelitem.name,
                callback_data=ActionPanelItem(
                    id=actionpanelitem.actionpanelitemcode,
                    hotkeycode=hotkey.hotkeycode,
                    hk_list=(
                        len(hotkey_items) > 1 if hotkey_items is not None else False
                    ),
                ),
            )
    if current_panel.page > 2:
        kb.button(
            text="⬅️",
            callback_data=ActionpanelGoods(
                acitem_id=current_panel.acitem_id,
                dir=True,
                page=2,
                ctx=current_panel.ctx,
                act_par_code=0,
            ),
        )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_changeComp(client: Clients):
    kb = InlineKeyboardBuilder()
    for cash in client.autologins:
        name = (
            f"{cash.shopcode}-{cash.cashcode}"
            if cash.cashcode > 1
            else str(cash.shopcode)
        )
        kb.button(
            text=name,
            callback_data=ChangeComp(
                id=cash.id,
                shopcode=cash.shopcode,
                cashcode=cash.cashcode,
            ),
        )
    if Roles(client.role.role) in [Roles.ADMIN, Roles.TEHPOD, Roles.SAMAN_PROVIDER, Roles.PREMIER_PROVIDER,
                                   Roles.ROSSICH_PROVIDER, Roles.ALKOTORG_PROVIDER]:
        kb.button(text="Удалить все 🖥❌", callback_data="artix_delete_all_save_cash")
    kb.adjust(1)
    kb.row(
        InlineKeyboardButton(text="Добавить 🖥➕", callback_data="artix_add_cash"),
        InlineKeyboardButton(text="Удалить 🖥❌", callback_data="artix_delete_cash"),
    )

    return kb.as_markup()


def kb_delComp(client: Clients):
    kb = InlineKeyboardBuilder()
    for cash in client.autologins:
        kb.button(
            text=f"{cash.shopcode}",
            callback_data=DelComp(id=cash.id, shopcode=cash.shopcode),
        )

    kb.adjust(1)
    return kb.as_markup()


def kb_degustation_prepare_commit():
    kb = InlineKeyboardBuilder()
    kb.button(text="Добавить еще ➕", callback_data="online_check_degustation")
    kb.button(text="Готово ✅", callback_data="commit_degustation")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_rozlivalco_dubl_amark():
    kb = InlineKeyboardBuilder()
    kb.button(text="Список сканированных товаров ⏳", callback_data="load_rozliv_alco")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_rozlivalco_not_found_barcode():
    kb = InlineKeyboardBuilder()
    kb.button(text="Добавить товар", callback_data="new_barcode")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_rozlivalco_prepare_commit():
    kb = InlineKeyboardBuilder()
    kb.button(text="Добавить еще ➕", callback_data="more_alco")
    kb.button(text="Готово ✅", callback_data="commit_rozliv_alco")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_onlinecheck_basic_prepare_commit():
    kb = InlineKeyboardBuilder()
    kb.button(text="Добавить еще ➕", callback_data="online_check_basic_more_position")
    kb.button(text="Продолжить ✅", callback_data="onlinecheck_basic_payment")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_onlinecheck_basic_dublicate_position():
    kb = InlineKeyboardBuilder()
    kb.button(
        text="Список сканированных товаров ⏳",
        callback_data="onlinecheck_basic_duplicate_position",
    )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_sub_to_channel() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Подписаться", url="https://t.me/egais116")
    kb.adjust(1)
    return kb.as_markup()


def kb_fail_sub(txt: str, cb_data: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Подписаться", url="https://t.me/egais116")
    kb.button(text=txt, callback_data=cb_data)
    kb.adjust(1)
    return kb.as_markup()


def kb_test() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text="открыть",
        url="http://192.168.2.182:8080/vnc/vnc.html?path=vnc/?token=10.8.32.222:5900&password=eghfdktybt",
    )
    kb.adjust(1)
    return kb.as_markup()
