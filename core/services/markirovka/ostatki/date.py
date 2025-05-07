from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from core.utils import texts


async def date_ostatki(call: CallbackQuery, state: FSMContext):
    await call.answer(texts.develop)
