from aiogram.fsm.state import StatesGroup, State


class MarkirovkaMenu(StatesGroup):
    enter_inn = State()
    delete_autologins = State()
    menu = State()
    accept_ttn = State()
    inventory_choise_pg = State()
    inventory_start = State()
    ostatki_actual = State()
