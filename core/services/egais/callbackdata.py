from datetime import datetime

from aiogram.filters.callback_data import CallbackData


class DraftBeerAddProfiles(CallbackData, prefix="draftbeer_add_profiles"):
    id: int


class DelComp(CallbackData, prefix="delcomp"):
    id: int
    shopcode: int


class ChangeComp(CallbackData, prefix="changeComp"):
    id: int
    shopcode: int
    cashcode: int


class OverpriceTTN(CallbackData, prefix="overprice_ttn"):
    procent: float
