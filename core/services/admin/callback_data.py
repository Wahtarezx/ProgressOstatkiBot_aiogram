from aiogram.filters.callback_data import CallbackData


class DeleteCashFromAcceptlist(CallbackData, prefix="del_from_acceptlist"):
    cash: str


class CBChooseRole(CallbackData, prefix="choose_role"):
    role: str


class CBChooseForeman(CallbackData, prefix="f_vers"):
    f_vers: str
