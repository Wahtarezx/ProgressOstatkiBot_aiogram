from aiogram.filters.callback_data import CallbackData


class DaysHistorySales(CallbackData, prefix="days_history_sales"):
    days: int
