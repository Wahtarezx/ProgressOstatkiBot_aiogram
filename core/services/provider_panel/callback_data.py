from aiogram.filters.callback_data import CallbackData


class Provider(CallbackData, prefix="sel_provider"):
    name: str
