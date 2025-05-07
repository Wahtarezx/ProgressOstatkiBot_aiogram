from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.services.edo.schemas.login.models_delete import DeleteProfiles
from core.services.markirovka.callbackdata import *
from core.services.markirovka.ofdplatforma import get_pg_info
from core.services.markirovka.trueapi import get_actions


def choise_edo_provider(thumbprint: str):
    kb = InlineKeyboardBuilder()
    kb.button(
        text="Честный знак", callback_data=ChoiseEdoProvider(type=1, tb=thumbprint)
    )
    kb.button(
        text="Платформа ОФД", callback_data=ChoiseEdoProvider(type=2, tb=thumbprint)
    )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def select_account_autologin(accounts):
    kb = InlineKeyboardBuilder()
    for acc in accounts:
        kb.button(
            text=acc.fio,
            callback_data=ChoiseAccountLogin(type=acc.edo_provider, inn=acc.inn),
        )
    kb.adjust(1)
    kb.row(
        InlineKeyboardButton(
            text="Добавить 👤➕", callback_data="markirovka_enter_inn"
        ),
        InlineKeyboardButton(
            text="Удалить 👤❌", callback_data="markirovka_choice_delete_autologin"
        ),
    )
    return kb.as_markup()


def kb_delete_autologin(del_profiles: DeleteProfiles):
    kb = InlineKeyboardBuilder()
    for p in del_profiles.profiles:
        if p.to_delete:
            kb.button(text=f"❌{p.fio}", callback_data=DeleteAutoLogin(inn=p.inn))
        else:
            kb.button(text=p.fio, callback_data=DeleteAutoLogin(inn=p.inn))
    kb.adjust(1)

    buttons = []
    if any([p.to_delete for p in del_profiles.profiles]):
        buttons.append(
            InlineKeyboardButton(
                text="Удалить 👤❌", callback_data="markirovka_delete_autologin"
            )
        ),
    buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="markirovka")),
    kb.row(*buttons)

    return kb.as_markup()


def kb_start_markirovka():
    kb = InlineKeyboardBuilder()
    kb.button(text="Остатки", callback_data="markirovka_ostatki")
    kb.button(text="Накладные", callback_data="markirovka_documents")
    kb.button(text="Инвентаризация", callback_data="markirovka_inventory")
    kb.button(text="Разливное пиво", callback_data="draftbeer_menu")
    kb.adjust(2, repeat=True)
    return kb.as_markup()


def kb_markirovka_doc_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Подтвердить накладные", callback_data="markirovka_ttn_accept")
    kb.button(
        text="Информация о последних накладных", callback_data="markirovka_ttn_info"
    )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


async def kb_choice_product_group(product_groups: list):
    kb = InlineKeyboardBuilder()
    for pg in product_groups:
        pg_info = await get_pg_info(pg)
        if pg_info is None:
            raise ValueError(f"Данная товарная группа '{pg.name}' не найдена")
        kb.button(
            text=pg_info.name,
            callback_data=ChoisePG(
                id=pg_info.group_id, name=pg, i_v_b=pg_info.is_volume_balance
            ),
        )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


async def kb_actions(pg_name: str, pg_id: str):
    kb = InlineKeyboardBuilder()
    pg_info = await get_pg_info(pg_name)
    actions = get_actions(pg_info.is_volume_balance)
    if pg_id in actions.get("except_pg", []):
        raise ValueError(
            f'Для данной товарной группы "{pg_name}" не доступен вывод из оборота'
        )
    for doc in actions["docs"]:
        if not doc["all"]:
            access_pg = doc.get("access_pg", [])
            except_pg = doc.get("except_pg", [])
            if len(access_pg) > 0:
                if pg_id not in doc.get("access_pg", []):
                    continue
            elif len(except_pg) > 0:
                if pg_id in doc.get("except_pg", []):
                    continue
        kb.button(
            text=doc["name"],
            callback_data=ChoiseAction(
                i_v_b=pg_info.is_volume_balance,
                doc_type=doc["document_type"],
                action=doc["action"],
            ),
        )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_ostatki_start_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Актуальные остатки", callback_data="ostatki_actual")
    kb.button(text="Выбрать дату", callback_data="ostatki_data")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


async def kb_ostatki_actual_menu(product_groups: list, groups: list):
    kb = InlineKeyboardBuilder()
    if not groups:
        kb.button(text="Выбрать все позиции✅", callback_data="ostatki_select_all")
    for pg in product_groups:
        pg_info = await get_pg_info(pg)
        if pg_info is None:
            raise ValueError(f"Данная товарная группа '{pg}' не найдена")
        if pg in groups:
            kb.button(
                text=f"✅{pg_info.name}",
                callback_data=ChoisePG(
                    id=pg_info.group_id,
                    name=pg,
                    i_v_b=pg_info.is_volume_balance,
                ),
            )
        else:
            kb.button(
                text=pg_info.name,
                callback_data=ChoisePG(
                    id=pg_info.group_id,
                    name=pg,
                    i_v_b=pg_info.is_volume_balance,
                ),
            )
    if groups:
        kb.button(text="Продолжить➡️", callback_data="ostatki_actual_all")

    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_scan_inventory(only_close: bool = False):
    kb = InlineKeyboardBuilder()
    if not only_close:
        kb.button(text="Подробная информация", callback_data="chz_inventory_info")
    kb.button(text="Перейти к завершению", callback_data="chz_inventory_confirm_end")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_confirm_inventory_end():
    kb = InlineKeyboardBuilder()
    kb.button(text="Подтвердить✅", callback_data="chz_inventory_end")
    kb.button(text="⬅️ Назад", callback_data="chz_inventory_info")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_again_price():
    kb = InlineKeyboardBuilder()
    kb.button(text="Да", callback_data="yes_again_price")
    kb.button(text="нет", callback_data="no_again_price")
    kb.adjust(1, repeat=True)
    return kb.as_markup()
