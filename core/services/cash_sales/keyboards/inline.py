from datetime import datetime

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.services.cash_sales import callback_data as cb_data


def kb_select_days_sales() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    past_days_current_year = (
        datetime.now()
        - datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0, month=1, day=1
        )
    ).days
    keyboard.button(text="Вчера", callback_data=cb_data.DaysHistorySales(days=1))
    keyboard.button(text="За 7 дней", callback_data=cb_data.DaysHistorySales(days=7))
    keyboard.button(text="За 30 дней", callback_data=cb_data.DaysHistorySales(days=30))
    keyboard.button(
        text="За текущий год",
        callback_data=cb_data.DaysHistorySales(days=past_days_current_year),
    )
    keyboard.button(
        text="За всё время", callback_data=cb_data.DaysHistorySales(days=366 * 100)
    )
    keyboard.button(text="Написать период самому", callback_data="enter_period_sales")
    keyboard.adjust(1)
    return keyboard.as_markup()
