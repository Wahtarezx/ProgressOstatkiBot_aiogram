from aiogram.fsm.state import State, StatesGroup


class CreateBonusCardState(StatesGroup):
    phone = State()
    number_card = State()
    fio = State()
