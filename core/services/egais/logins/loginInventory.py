import re

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from core.keyboards.inline import kb_inventory
from core.loggers.egais_logger import LoggerEGAIS
from core.utils import texts
from core.utils.states import Inventory_EGAIS


async def menu(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Инвентаризация")
    await state.set_state(Inventory_EGAIS.menu)
    await call.message.answer(texts.inventory, reply_markup=kb_inventory())
