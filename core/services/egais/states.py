from aiogram.fsm.state import State, StatesGroup


class DraftBeerAdd(StatesGroup):
    cis = State()
    expDate = State()
    prepare_commit = State()


class DegustationState(StatesGroup):
    bcode = State()
    name = State()
    amark = State()
    price = State()
    mail = State()
    prepare_commit = State()


class RozlivAlcoState(StatesGroup):
    bcode = State()
    amark = State()
    quantity = State()
    prepare_commit = State()
