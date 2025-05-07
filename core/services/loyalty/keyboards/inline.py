from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .. import callback_data as cb_data


def kb_loyalty_menu() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Добавить бонусную карту", callback_data="create_bonus_card")
    keyboard.adjust(1)
    return keyboard.as_markup()


def kb_skip_number_card() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(
        text="Пропустить ввод номера карты",
        callback_data="create_bonus_card_skip_cardbonus",
    )
    keyboard.adjust(1)
    return keyboard.as_markup()
