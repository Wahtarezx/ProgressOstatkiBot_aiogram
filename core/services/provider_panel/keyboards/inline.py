from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.database.models_enum import providers, Roles
from .. import callback_data as cb_data


def kb_provider_start() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📊Аналитика", callback_data="provider_analytics")
    keyboard.adjust(1)
    return keyboard.as_markup()


def kb_select_providers(providers: list[Roles]) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    for provider in providers:
        keyboard.button(
            text=provider.value, callback_data=cb_data.Provider(name=provider.value)
        )
    keyboard.adjust(1)
    return keyboard.as_markup()
