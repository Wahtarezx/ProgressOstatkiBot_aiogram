from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import get_inns_by_provider
from core.database.models_enum import Roles, providers
from core.database.query_BOT import Database
from core.loggers.egais_logger import LoggerEGAIS
from core.services.provider_panel.callback_data import Provider
from core.services.provider_panel.keyboards.inline import (
    kb_provider_start,
    kb_select_providers,
)
from core.utils import texts

router = Router()


@router.message(Command("panel"))
async def panel(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("/panel")
    db = Database()
    client_db = await db.get_client_info(message.chat.id)
    role = Roles(client_db.role.role)
    if Roles(client_db.role.role) not in [Roles.ADMIN, Roles.TEHPOD, *providers()]:
        log_e.error("У пользователя не хватает прав смотреть раздел поставщика")
        await message.answer(
            texts.error_head + "У вас не хватает прав для просмотра раздела поставщика"
        )
        return

    if role in [Roles.ADMIN, Roles.TEHPOD]:
        await message.answer(
            "Выберите поставщика от которого вы хотите получить данные",
            reply_markup=kb_select_providers(providers()),
        )
    else:
        await state.update_data(provider_inns=await get_inns_by_provider(role))
        await message.answer(
            "Выберите нужный пункт меню", reply_markup=kb_provider_start()
        )


@router.callback_query(Provider.filter())
async def choose_provider(
    call: CallbackQuery, state: FSMContext, callback_data: Provider, log_e: LoggerEGAIS
):
    log_e.info(f'Выбрали поставщика "{callback_data.name}"')
    await state.update_data(
        provider_inns=await get_inns_by_provider(Roles(callback_data.name))
    )
    await call.message.edit_text(
        "Выберите нужный пункт меню", reply_markup=kb_provider_start()
    )
