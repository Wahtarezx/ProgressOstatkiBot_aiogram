from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from core.database.models_enum import Roles
from core.database.query_BOT import Database
from core.loggers.egais_logger import LoggerEGAIS
from core.utils import texts
from core.utils.foreman.pd_model import ForemanCash
from core.utils.states import StateOstatki
from ..callback_data import Ostatki, OstatkiType
from ..keyboards.inline import kb_ostatki_entity, kb_ostatki, kb_type_ostatki

router = Router()
db = Database()


@router.callback_query(F.data == "ostatki")
async def cmd_ostatki(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    log_e.button("Остатки")
    client = await db.get_client_info(call.from_user.id)
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    await state.set_state(StateOstatki.choose_entity)
    if Roles(client.role.role) != Roles.USER:
        await call.message.edit_text(
            "Выберите тип остатков", reply_markup=kb_type_ostatki()
        )
    else:
        await call.message.edit_text(
            texts.choose_entity, reply_markup=kb_ostatki_entity(cash)
        )


@router.callback_query(OstatkiType.filter())
async def choose_entity(
    call: CallbackQuery,
    state: FSMContext,
    callback_data: OstatkiType,
    log_e: LoggerEGAIS,
):
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    log_e.info(f'Выбрали тип остатков "{callback_data.file_type}"')
    await state.update_data(ostatki_type=callback_data.file_type)
    await call.message.edit_text(
        texts.choose_entity, reply_markup=kb_ostatki_entity(cash)
    )


@router.callback_query(Ostatki.filter())
async def menu(
    call: CallbackQuery, state: FSMContext, callback_data: Ostatki, log_e: LoggerEGAIS
):
    log_e.info(f'Выбрали Юр.Лицо "{callback_data.inn}"')
    await state.set_state(StateOstatki.menu)
    await state.update_data(
        ostatki_inn=callback_data.inn, ostatki_fsrar=callback_data.fsrar
    )
    await call.message.edit_text(texts.ostatki, reply_markup=kb_ostatki())
