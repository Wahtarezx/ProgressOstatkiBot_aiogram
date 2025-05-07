from aiogram.filters.callback_data import CallbackData

# ====TTNS====


class ChooseEntity(CallbackData, prefix="entity"):
    inn: str
    fsrar: str
    port: str
    ip: str


class AcceptTTN(CallbackData, prefix="accept_ttn"):
    id_f2r: str
    id_wb: str
    ttn: str
    inn: str


class ResendTTN(CallbackData, prefix="resend_ttn"):
    ttn_egais: str
    shipper_inn: str


class SendAcceptTTN(CallbackData, prefix="send_ttn"):
    id_f2r: str
    id_wb: str
    ttn: str
    auto: bool
    alco: bool


class ListTTN(CallbackData, prefix="ttn_list"):
    ttnload: str
    ttn_e: str


class SelectDcode(CallbackData, prefix="dcode"):
    dcode: int
    op_mode: int
    tmctype: int


class SelectMeasure(CallbackData, prefix="measure"):
    measure: int
    op_mode: int
    tmctype: int
    qdefault: int  # Количество по умолчанию


class DeleteCashFromWhitelist(CallbackData, prefix="del_from_whitelist"):
    cash: str


class VolumeDraftBeer(CallbackData, prefix="volume_draftbeer"):
    volume: int
