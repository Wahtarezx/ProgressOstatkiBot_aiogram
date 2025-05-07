from aiogram.fsm.state import State, StatesGroup


class StateSalesPeriod(StatesGroup):
    start_date = State()
    end_date = State()
    finish = State()
