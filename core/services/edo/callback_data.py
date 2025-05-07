from aiogram.filters.callback_data import CallbackData


class ChoiseAccountLogin(CallbackData, prefix="mark_acc_log"):
    inn: str


class DeleteAutoLogin(CallbackData, prefix="mark_del_autologin"):
    inn: str


class DocForAccept(CallbackData, prefix="mark_accept_doc"):
    id: str


class SelectEdoProvider(CallbackData, prefix="select_edo"):
    id: int


class SendAcceptDoc(CallbackData, prefix="send_doc_accept"):
    id: str


class DocForInfo(CallbackData, prefix="mark_info_doc"):
    id: str


class DraftBeerAddProfiles(CallbackData, prefix="draftbeer_add_profiles"):
    id: int


class DraftBeerMOD(CallbackData, prefix="draftbeer_mod"):
    fias: str
    kpp: str
