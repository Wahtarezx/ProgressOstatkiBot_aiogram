from aiogram.fsm.state import State, StatesGroup


class AddCashAcceptlist(StatesGroup):
    enter_cashNumber = State()
    enter_inn = State()


class StateChooseRole(StatesGroup):
    phone = State()
    end = State()


class CreatePostState(StatesGroup):
    text = State()
    prepared = State()
    accept_filter = State()
    text_filter = State()
    prepare_filter = State()
