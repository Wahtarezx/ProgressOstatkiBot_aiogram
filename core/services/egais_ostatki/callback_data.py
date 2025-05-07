from aiogram.filters.callback_data import CallbackData


class OstatkiType(CallbackData, prefix="ostatki_type"):
    file_type: str


class Ostatki(CallbackData, prefix="ostatki"):
    inn: str
    fsrar: str


class OstatkiLast(CallbackData, prefix="ost_last"):
    inn: str
    fsrar: str


class OstatkiList(CallbackData, prefix="ostatki_menu_list"):
    inn: str
    fsrar: str


class OstatkiChooseList(CallbackData, prefix="ost_list"):
    file_name: str
