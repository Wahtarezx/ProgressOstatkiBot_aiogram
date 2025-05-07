from aiogram.fsm.state import State, StatesGroup


class MarkirovkaMenu(StatesGroup):
    enter_inn = State()
    delete_autologins = State()
    menu = State()
    accept_ttn = State()
    inventory_choise_pg = State()
    inventory_start = State()
    ostatki_actual = State()


class DraftBeerAdd(StatesGroup):
    cis = State()
    expDate = State()
    prepare_commit = State()
