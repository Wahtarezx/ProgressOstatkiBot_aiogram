from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from core.loggers.markirovka_logger import LoggerZnak
from core.services.edo.keyboards import inline

router = Router()
