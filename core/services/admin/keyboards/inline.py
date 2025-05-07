from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.database.modelBOT import Clients
from core.database.models_enum import Roles
from core.services.admin.callback_data import (
    DeleteCashFromAcceptlist,
    CBChooseRole,
    CBChooseForeman,
)


def kb_admins(client: Clients):
    kb = InlineKeyboardBuilder()
    kb.button(text="Приём без сканирования", callback_data="acceptTTN_admin")
    kb.button(text="Поменять роль пользователя", callback_data="choose_role")
    kb.button(text="Создать рассылку", callback_data="create_post")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_send_post() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Отправить всем пользователям", callback_data="send_post_all")
    keyboard.button(text="Отправить по фильтру", callback_data="send_post_filter")
    keyboard.adjust(1)
    return keyboard.as_markup()


def kb_send_post_choose_foreman() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Ubuntu 14", callback_data=CBChooseForeman(f_vers="14"))
    keyboard.button(text="Ubuntu 18", callback_data=CBChooseForeman(f_vers="18"))
    keyboard.button(text="Всем", callback_data=CBChooseForeman(f_vers="18,14"))
    keyboard.adjust(1)
    return keyboard.as_markup()


def kb_send_post_filter_continue() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Продолжить➡️", callback_data="send_post_filter_continue")
    keyboard.adjust(1)
    return keyboard.as_markup()


def kb_send_post_all() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Отправить рассылку✅", callback_data="send_post")
    keyboard.button(text="Переделать🔄", callback_data="send_post_all")
    keyboard.adjust(1)
    return keyboard.as_markup()


def kb_send_post_filter() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(
        text="Отправить рассылку✅", callback_data="send_post_filter_accept"
    )
    keyboard.button(text="Переделать🔄", callback_data="send_post_filter_continue")
    keyboard.adjust(1)
    return keyboard.as_markup()


def kb_list_roles():
    kb = InlineKeyboardBuilder()
    for role in Roles:
        kb.button(text=role.value, callback_data=CBChooseRole(role=role.value))
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_acceptTTN_admin():
    kb = InlineKeyboardBuilder()
    kb.button(text="Добавить в список", callback_data="add_in_acceptTTN_list")
    kb.button(text="Удалить из списка", callback_data="remove_from_acceptTTN_list")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_acceptTTN_choose_inn():
    kb = InlineKeyboardBuilder()
    kb.button(text="Разрешить принимать все накладные", callback_data="acceptTNN_all")
    kb.button(text="Ввести ИНН поставщиков", callback_data="acceptTNN_select")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


async def kb_delete_cash_from_acceptlist(may_accept_caches: list[Clients]):
    kb = InlineKeyboardBuilder()
    for cash in may_accept_caches:
        kb.button(
            text=f'{cash.cash_number.split("-")[1]}',
            callback_data=DeleteCashFromAcceptlist(cash=cash.cash_number),
        )
    kb.adjust(1, repeat=True)
    return kb.as_markup()
