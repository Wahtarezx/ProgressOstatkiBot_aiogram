from pathlib import Path

from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.utils.foreman.pd_model import ForemanCash
from ..callback_data import Ostatki, OstatkiChooseList, OstatkiType


def kb_type_ostatki():
    kb = InlineKeyboardBuilder()
    kb.button(text="Excel", callback_data=OstatkiType(file_type="xls"))
    kb.button(text="XML", callback_data=OstatkiType(file_type="xml"))
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_ostatki():
    kb = InlineKeyboardBuilder()
    kb.button(text="Последние остатки", callback_data="send_last_ostatki")
    kb.button(text="Список по датам", callback_data="select_list_ostatki")
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_ostatki_entity(cash: ForemanCash):
    kb = InlineKeyboardBuilder()
    if cash.artix_shopname and cash.fsrar:
        kb.button(
            text=cash.artix_shopname,
            callback_data=Ostatki(inn=cash.inn, fsrar=cash.fsrar),
        )
    if cash.artix_shopname2 and cash.fsrar2:
        kb.button(
            text=cash.artix_shopname2,
            callback_data=Ostatki(inn=cash.inn2, fsrar=cash.fsrar2),
        )
    kb.adjust(1, repeat=True)
    return kb.as_markup()


def kb_choose_list_ostatki(list_files: list[Path, str]):
    kb = InlineKeyboardBuilder()
    for file_path, date in list_files:
        kb.button(text=date, callback_data=OstatkiChooseList(file_name=str(file_path)))
    kb.adjust(1, repeat=True)
    return kb.as_markup()
