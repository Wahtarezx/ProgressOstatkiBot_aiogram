from aiogram.fsm.state import State, StatesGroup


class OnlineChecksTTNState(StatesGroup):
    prepare_commit = State()
    enter_overprice = State()
    valut = State()


class OnlineChecksBasicState(StatesGroup):
    scan_or_photo = State()
    product_name = State()
    product_price = State()
    product_markirovka = State()
    product_excisemark = State()
    prepare_commit = State()
    payment = State()
