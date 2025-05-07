from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from core.database.edo.query import EdoDB
from core.loggers.markirovka_logger import LoggerZnak
from core.services.edo.callback_data import SelectEdoProvider
from core.services.edo.keyboards import inline
from core.services.edo.schemas.login.models import EnumEdoProvider
from core.services.markirovka.trueapi import TrueApi
from core.utils import texts
from core.utils.edo_providers.factory import EDOFactory
from core.utils.redis import RedisConnection

router = Router()

edodb = EdoDB()


@router.callback_query(F.data == "markirovka_documents")
async def documents_menu(
    call: CallbackQuery,
    state: FSMContext,
    log_m: LoggerZnak,
    redis_connection: RedisConnection,
    edo_factory: EDOFactory,
):
    log_m.button("Накладные")
    trueapi = await TrueApi.load_from_redis(redis_connection)
    profile_info = await trueapi.profile_info()
    may_providers_connect = await profile_info.get_providers_may_connect()

    if not may_providers_connect:
        log_m.error(f"У вас нет подключенных ЭДО провайдеров которых мы обслуживаем.")
        await call.message.edit_text(
            f"У вас нет подключенных ЭДО провайдеров которых мы обслуживаем."
        )
        return

    edoprovider = None
    if len(may_providers_connect) == 1:
        edoprovider = await edo_factory.create_edo_operator(
            may_providers_connect[0].edo_operator_id
        )
        await state.update_data(
            current_EdoOperator=may_providers_connect[0].model_dump_json()
        )
        log_m.debug(
            f"Выбран ЭДО провайдер: {may_providers_connect[0].edo_operator_name}"
        )
    else:
        for edo_provider in may_providers_connect:
            if edo_provider.is_main_operator:
                edoprovider = await edo_factory.create_edo_operator(
                    edo_provider.edo_operator_id
                )
                log_m.debug(f"Выбран ЭДО провайдер: {edo_provider.edo_operator_name}")
                await state.update_data(
                    current_EdoOperator=may_providers_connect[0].model_dump_json()
                )
    if edoprovider is None:
        await call.message.edit_text(
            "Выберите провайдера ЭДО",
            reply_markup=inline.kb_select_edo_provider(may_providers_connect),
        )
    else:
        await state.update_data(await edoprovider.save_to_redis(redis_connection))
        await call.message.edit_text(
            texts.markirovka_doc_menu, reply_markup=inline.kb_markirovka_doc_menu()
        )


@router.callback_query(SelectEdoProvider.filter())
async def select_edo_provider(
    call: CallbackQuery,
    log_m: LoggerZnak,
    callback_data: SelectEdoProvider,
    edo_factory: EDOFactory,
):
    log_m.info(f"Выбрали ЭДО провайдера: {EnumEdoProvider(callback_data.id).name}")
    await edo_factory.create_edo_operator(callback_data.id)
    await call.message.edit_text(
        texts.markirovka_doc_menu, reply_markup=inline.kb_markirovka_doc_menu()
    )
