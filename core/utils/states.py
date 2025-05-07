from aiogram.fsm.state import State, StatesGroup


class TestState(StatesGroup):
    uuid = State()


class Auth(StatesGroup):
    send_cash_number = State()
    send_password = State()


class Menu(StatesGroup):
    menu = State()


class StateOstatki(StatesGroup):
    enter_cashNumber = State()
    choose_entity = State()
    inn = State()
    menu = State()
    LAST_OSTATKI = State()
    LIST_OSTATKI = State()
    ERROR = State()


class RefState(StatesGroup):
    enter_cashNumber = State()


class StateTTNs(StatesGroup):
    enter_cashNumber = State()
    choose_entity = State()
    inn = State()
    menu = State()
    accept_ttn = State()
    choose_divirgence_ttn = State()


class Goods(StatesGroup):
    enter_cash_number = State()
    choose_entity = State()
    inn = State()
    menu = State()


class GenerateBarcode(StatesGroup):
    dcode = State()
    measure = State()
    barcode = State()
    price = State()
    name = State()
    final = State()


class AddToCashBarcode(StatesGroup):
    dcode = State()
    measure = State()
    one_or_more_draftbeer = State()
    scan_more_draftbeer = State()
    volume_draftbeer = State()
    expirationdate_draftbeer = State()
    barcode = State()
    price = State()
    name = State()
    final = State()
    is_touch = State()


class ChangePrice(StatesGroup):
    barcode = State()
    price = State()
    final = State()


class Inventory_EGAIS(StatesGroup):
    enter_cashNumber = State()
    choose_entity = State()
    inn = State()
    menu = State()
    scaning = State()


class ResendTTNfromText(StatesGroup):
    enter_ttnEgais = State()


class AddCashWhitelist(StatesGroup):
    enter_cashNumber = State()


class AddCashAcceptlist(StatesGroup):
    enter_cashNumber = State()
    enter_inn = State()


class DraftBeer(StatesGroup):
    enter_cashNumber = State()
