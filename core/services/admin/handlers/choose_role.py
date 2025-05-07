import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from core.database.query_BOT import Database
from core.loggers.egais_logger import LoggerEGAIS
from core.utils import texts
from core.utils.commands import update_user_commands
from ..keyboards.inline import kb_list_roles, kb_admins
from ..callback_data import CBChooseRole
from ..states import StateChooseRole

router = Router()
db = Database()


@router.callback_query(F.data == "choose_role")
async def choose_role(call: CallbackQuery, log_e: LoggerEGAIS):
    log_e.button("Поменять роль пользователя")
    await call.message.edit_text("Выберите роль", reply_markup=kb_list_roles())


@router.callback_query(CBChooseRole.filter())
async def choose_role(
    call: CallbackQuery,
    callback_data: CBChooseRole,
    state: FSMContext,
    log_e: LoggerEGAIS,
):
    log_e.info(f'Выбрали роль "{callback_data.role}"')
    await state.update_data(choose_role=callback_data.role)
    await call.message.edit_text(
        "Напишите ответным сообщением сотовый пользователя\n" "Например: 7912345678",
    )
    await state.set_state(StateChooseRole.phone)


@router.message(StateChooseRole.phone)
async def end_choose_role(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.info(f'Написали сотовый пользователя "{message.text}"')
    phone = "".join(re.findall(r"\d+", message.text))
    log_e.debug(f'Преоброзовал сотовый "{phone}"')
    client = await db.get_client_info_by_phone(phone)
    data = await state.get_data()
    if client is None:
        log_e.error(
            f'Пользователь с данным сотовым "{message.text}" не зарегестрирован в боте'
        )
        await message.answer(
            texts.error_head
            + f'Пользователь с ID "{message.text}" не зарегестрирован в боте'
        )
        return
    await db.update_role(user_id=client.user_id, role=data.get("choose_role"))
    client = await db.get_client_info_by_phone(phone)
    await update_user_commands(message.bot, client)
    await message.answer(
        texts.success_head
        + f'Пользователю с сотовым "{message.text}" установлена роль "{data.get("choose_role")}"',
        reply_markup=kb_admins(client),
    )
    await message.bot.send_message(
        client.chat_id,
        texts.success_head + f'Вам установлена роль "{data.get("choose_role")}',
    )
    log_e.success(
        f'Пользователю с сотовым "{message.text}" установлена роль "{data.get("choose_role")}"'
    )
    await state.set_state(StateChooseRole.end)
