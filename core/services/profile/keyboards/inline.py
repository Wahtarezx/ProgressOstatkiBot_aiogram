from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .. import callback_data as cb_data


def kb_profile() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="⬅️ Назад", callback_data="back_to_main_menu")
    keyboard.adjust(1)
    return keyboard.as_markup()
