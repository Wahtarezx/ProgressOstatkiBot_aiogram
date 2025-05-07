from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.services.edo.callback_data import (
    SelectEdoProvider,
    SendAcceptDoc,
    ChoiseAccountLogin,
    DeleteAutoLogin,
    DocForAccept,
    DocForInfo,
    DraftBeerMOD,
)
from core.services.edo.schemas.login.models_delete import DeleteProfiles
from core.services.markirovka.database.model import AutoLoginMarkirovka
from core.services.markirovka.pd_models.gismt import EdoOperator, MODS
from core.utils.edo_providers.base_model import BaseDocument


def select_account_autologin(accounts: AutoLoginMarkirovka):
    kb = InlineKeyboardBuilder()
    for acc in accounts:
        kb.button(text=acc.fio, callback_data=ChoiseAccountLogin(inn=acc.inn))
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
    # kb.button(text="Остатки", callback_data='markirovka_ostatki')
    kb.button(text="Накладные", callback_data="markirovka_documents")
    # kb.button(text="Инвентаризация", callback_data='markirovka_inventory')
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


def kb_select_edo_provider(edoproviders: list[EdoOperator]):
    kb = InlineKeyboardBuilder()
    for edoprovider in edoproviders:
        kb.button(
            text=edoprovider.edo_operator_name,
            callback_data=SelectEdoProvider(id=edoprovider.edo_operator_id),
        )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_select_doc_for_accept(docs: list[BaseDocument]):
    kb = InlineKeyboardBuilder()
    for doc in docs:
        kb.button(
            text=doc.doc_name,
            callback_data=DocForAccept(
                id=doc.doc_id,
            ),
        )
    kb.button(text="Подтвердить все накладные✅", callback_data="accept_all_EDO_docs")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_select_doc_for_info(docs: list[BaseDocument]):
    kb = InlineKeyboardBuilder()
    for doc in docs:
        kb.button(
            text=doc.doc_name,
            callback_data=DocForInfo(
                id=doc.doc_id,
            ),
        )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_doc_info_for_accept(doc_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="Подтвердить накладную", callback_data=SendAcceptDoc(id=doc_id))
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_back_to_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text=f"⬅️ Назад", callback_data="back_to_menu_markirovka")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_ostatki_start_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Актуальные остатки", callback_data="ostatki_actual")
    kb.button(text="Выбрать дату", callback_data="ostatki_data")
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


def kb_draftbeer_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Поставить кегу на учет", callback_data="draftbeer_add")
    kb.button(text="Остатки пива", callback_data="draftbeer_balance")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_draftbeer_add_mods(mods: MODS):
    kb = InlineKeyboardBuilder()
    for i, mod in enumerate(mods.result, start=1):
        kb.button(
            text=f"{i}. {mod.address}",
            callback_data=DraftBeerMOD(
                fias=mod.fiasId,
                kpp=mod.kpp,
            ),
        )
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
