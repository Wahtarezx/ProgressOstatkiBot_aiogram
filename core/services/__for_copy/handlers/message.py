from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from ..keyboards import inline, reply
from core.loggers.egais_logger import LoggerEGAIS
from core.utils import texts

router = Router()
