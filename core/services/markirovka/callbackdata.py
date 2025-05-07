from pathlib import Path

from aiogram.filters.callback_data import CallbackData

from core.services.egais.goods.pd_models import Dcode
from core.services.markirovka.enums import GroupIds


class ChoisePG(CallbackData, prefix="mrk_choice_pg"):
    id: GroupIds
    name: str
    i_v_b: bool


class ChoiseAction(CallbackData, prefix="mrk_choice_action"):
    action: str


class ChoiseEdoProvider(CallbackData, prefix="edo_provider"):
    type: int
    tb: str


class ChoiseAccountLogin(CallbackData, prefix="mark_acc_log"):
    inn: str


class DeleteAutoLogin(CallbackData, prefix="mark_del_autologin"):
    inn: str


class DocForAccept(CallbackData, prefix="mark_accept_doc"):
    id: str


class DocForInfo(CallbackData, prefix="mark_info_doc"):
    id: str


class SendAcceptMark(CallbackData, prefix="send_doc_accept"):
    id: str


class AddToTouchPanel(CallbackData, prefix="add_touch"):
    touch: bool


class ActionpanelGoods(CallbackData, prefix="actpanelgoods"):
    ctx: int  # actionpanel.context
    acitem_id: int  # actionpanelitem.actionpanelitemcode
    hotkeycode: int = 0
    hk_list: bool = False  # Если больше 1 горячих клавиш
    dir: bool  # Имеет ли кнопка подсписок
    page: int  # Если dir=True, то page=actionpanelparameter.parametervalue ИНАЧЕ page=0
    act_par_code: int  # actionpanelparameter.actionparametercode


class ActionPanelItem(CallbackData, prefix="actionpanelitem"):
    id: int  # actionpanelitem.actionpanelitemcode
    hotkeycode: int = 0
    hk_list: bool = False  # Если больше 1 горячих клавиш


class OnlineCheckTTN(CallbackData, prefix="online_check_ttn"):
    ttn_e: str  # Путь до накладной


class OnlineCheckTTNPage(CallbackData, prefix="online_check_ttn_page"):
    page: int  # Страница


class OnlineCheckTTNDcode(CallbackData, prefix="online_check_ttn_dcode"):
    dcode: int


class cbValut(CallbackData, prefix="valutes"):
    code: int
