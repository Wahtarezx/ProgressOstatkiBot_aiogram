from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.formatting import as_marked_section, Bold

import config
from core.database.edo.query import EdoDB
from core.loggers.markirovka_logger import LoggerZnak
from core.utils import texts
from core.utils.redis import RedisConnection
from ..callback_data import ChoiseAccountLogin, DeleteAutoLogin
from ..keyboards import inline
from ..schemas.login.models import EnumEdoProvider
from ..schemas.login.models_delete import DeleteProfiles, Profile
from ..states import MarkirovkaMenu
from ...markirovka.database.model import AutoLoginMarkirovka
from ...markirovka.trueapi import TrueApi

router = Router()

edodb = EdoDB()


@router.callback_query(F.data == "markirovka")
async def login_edo(call: CallbackQuery, state: FSMContext, log_m: LoggerZnak):
    log_m.button("Честный знак")
    accounts = await edodb.get_markirovka_autologins(call.message.chat.id)
    if accounts:
        await call.message.edit_text(
            "Выберите пользователя под которым хотите авторизоваться",
            reply_markup=inline.select_account_autologin(accounts),
        )
    else:
        await enter_inn(call, state, log_m)


@router.callback_query(F.data == "markirovka_enter_inn")
async def enter_inn(call: CallbackQuery, state: FSMContext, log_m: LoggerZnak):
    await state.set_state(MarkirovkaMenu.enter_inn)
    await call.message.edit_text(
        texts.auth_head + "Напишите ответным сообщением ваш <b>ИНН</b>"
    )
    log_m.info("Вводят ИНН для авторизации в ЧЗ")


@router.message(MarkirovkaMenu.enter_inn)
async def accept_inn(
    message: Message,
    state: FSMContext,
    log_m: LoggerZnak,
    redis_connection: RedisConnection,
):
    log_m.info(f'Ввели ИНН "{message.text}"')
    trueapi = TrueApi(inn_to_auth=message.text)
    await trueapi.create_token()
    user_info = await trueapi.get_user_info()
    profile_info = await trueapi.profile_info()
    await edodb.create_autologin(
        AutoLoginMarkirovka(
            chat_id=str(message.chat.id),
            inn=user_info.inn,
            fio=user_info.name,
            thumbprint=config.main_thumbprint,
            edo_provider=[
                e.edo_operator_id
                for e in profile_info.edo_operators
                if e.is_main_operator
            ][0],
        )
    )
    log_m.info(f'Добавил нового пользователя для автологина "{user_info.name}"')
    await trueapi.save_to_redis(redis_connection)
    await message.answer(
        texts.markirovka_menu, reply_markup=inline.kb_start_markirovka()
    )
    await state.update_data(trueapi_user_info=user_info.model_dump_json())
    await state.set_state(MarkirovkaMenu.menu)


@router.callback_query(ChoiseAccountLogin.filter())
async def menu_markirovka_after_select_acc(
    call: CallbackQuery,
    callback_data: ChoiseAccountLogin,
    state: FSMContext,
    log_m: LoggerZnak,
    redis_connection: RedisConnection,
):
    log_m.info(f'Выбрали аккаунт с ИНН "{callback_data.inn}"')
    trueapi = TrueApi(inn_to_auth=callback_data.inn)
    await trueapi.create_token()
    user_info = await trueapi.get_user_info()
    await trueapi.save_to_redis(redis_connection)
    await call.message.edit_text(
        texts.markirovka_menu, reply_markup=inline.kb_start_markirovka()
    )
    await state.update_data(trueapi_user_info=user_info.model_dump_json())
    await state.set_state(MarkirovkaMenu.menu)


@router.callback_query(F.data == "back_to_menu_markirovka")
async def back_to_menu(call: CallbackQuery, state: FSMContext, log_m: LoggerZnak):
    await state.set_state(MarkirovkaMenu.menu)
    await call.message.answer(
        texts.markirovka_doc_menu, reply_markup=inline.kb_markirovka_doc_menu()
    )
    await call.answer()
    log_m.button("Назад")


@router.callback_query(F.data == "markirovka_choice_delete_autologin")
async def start_delete_profiles(
    call: CallbackQuery, state: FSMContext, log_m: LoggerZnak
):
    log_m.button("Удалить пользователя из автологина")
    await state.set_state(MarkirovkaMenu.delete_autologins)
    accounts = await edodb.get_markirovka_autologins(call.message.chat.id)
    del_acc = DeleteProfiles(
        profiles=[Profile.model_validate(a.__dict__) for a in accounts]
    )
    await call.message.edit_text(
        "Выберите пользователя которого хотите удалить",
        reply_markup=inline.kb_delete_autologin(del_acc),
    )
    await state.update_data(delete_autologin=del_acc.model_dump_json())


@router.callback_query(DeleteAutoLogin.filter())
async def choise_profile_to_delete(
    call: CallbackQuery,
    state: FSMContext,
    log_m: LoggerZnak,
    callback_data: DeleteAutoLogin,
):
    log_m.info(f'Выбрали пользователя на удаление "{callback_data.inn}"')
    data = await state.get_data()
    del_acc = DeleteProfiles.model_validate_json(data["delete_autologin"])
    del_acc = del_acc.reverse_mark(callback_data.inn)
    await state.update_data(delete_autologin=del_acc.model_dump_json())
    await call.message.edit_text(
        "Выберите пользователя которого хотите удалить",
        reply_markup=inline.kb_delete_autologin(del_acc),
    )


@router.callback_query(F.data == "markirovka_delete_autologin")
async def delete_autologin_profiles(
    call: CallbackQuery, state: FSMContext, log_m: LoggerZnak
):
    await call.message.edit_text("Загрузка...")
    log_m.button("Удалили пользователей из автологина")
    data = await state.get_data()
    del_acc = DeleteProfiles.model_validate_json(
        data["delete_autologin"]
    ).profiles_to_delete()
    for acc in del_acc:
        await edodb.delete_autologin(acc.id)
    content = as_marked_section(
        Bold("Следующие пользователи убраны из быстрого доступа:"),
        *[p.fio for p in del_acc],
        marker="❌",
    )
    await call.message.edit_text(**content.as_kwargs())
