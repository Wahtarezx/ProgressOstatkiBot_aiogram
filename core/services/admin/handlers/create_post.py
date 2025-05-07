import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramRetryAfter
from aiogram.utils.formatting import Text, Code, as_marked_section, as_key_value

from core.database.query_BOT import Database
from core.loggers.egais_logger import LoggerEGAIS
from core.loggers.make_loggers import except_log
from core.utils import texts
from core.utils.foreman.foreman import get_cashes
from ..callback_data import CBChooseForeman
from ..keyboards import inline
from ..states import CreatePostState

router = Router()
db = Database()


@router.callback_query(F.data == "create_post")
async def create_post(call: CallbackQuery, log_e: LoggerEGAIS):
    log_e.button("Создать рассылку")
    await call.message.edit_text(
        "Выберите тип рассылки", reply_markup=inline.kb_send_post()
    )


@router.callback_query(F.data == "send_post_all")
async def create_post_all(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Отправить рассылку на всех")
    await call.message.edit_text(
        "Отправьте сообщение. В сообщение должно быть максимум 1 картинка"
    )
    await state.set_state(CreatePostState.text)


@router.message(CreatePostState.text)
async def prepare_send_post(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.info(f"Текст рекламной рассылки '{message.text}'")
    await state.update_data(create_post_msg_id=message.message_id)
    await state.set_state(CreatePostState.prepared)
    await message.bot.copy_message(
        message.chat.id,
        message.from_user.id,
        message.message_id,
        reply_markup=inline.kb_send_post_all(),
    )


@router.callback_query(F.data == "send_post")
async def send_post(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("Отправить рекламную рассылку")
    data = await state.get_data()
    await call.message.delete()
    await call.message.answer("Рассылка началась. Ожидайте...")
    count = 0
    for client in await db.get_all_clients():
        try:
            await call.bot.copy_message(
                client.user_id, call.from_user.id, data["create_post_msg_id"]
            )
            await asyncio.sleep(0.05)
            count += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except Exception as e:
            log_e.error(e)
            except_log.exception(e)
    await call.message.answer(f"Рассылка завершена. Отправлена {count} клиентам.")
    await state.clear()


@router.callback_query(F.data == "send_post_filter")
async def send_post_filter(call: CallbackQuery, log_e: LoggerEGAIS):
    log_e.button("Отправить рассылку по фильтру")
    await call.message.edit_text(
        "Выберите версию Ubuntu для рассылки",
        reply_markup=inline.kb_send_post_choose_foreman(),
    )


@router.callback_query(CBChooseForeman.filter())
async def send_post_filter(
    call: CallbackQuery,
    state: FSMContext,
    log_e: LoggerEGAIS,
    callback_data: CBChooseForeman,
):
    log_e.info(f"Выбрали версию Ubuntu {callback_data.f_vers}")
    await state.update_data(send_post_f_vers=callback_data.f_vers)
    content = as_marked_section(
        "Отправьте фильтр фактов из Foreman",
        as_key_value(
            "Пример",
            Code(
                'facts.artix_gost_1 > "2025-07-01" and facts.artix_gost_1 < "2025-08-01"'
            ),
        ),
        marker="",
    )
    await call.message.edit_text(**content.as_kwargs())
    await state.set_state(CreatePostState.accept_filter)


@router.message(CreatePostState.accept_filter)
async def accept_filter(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    log_e.info(f"Фильтр рекламной рассылки '{message.text}'")
    f_vers = [int(f) for f in data.get("send_post_f_vers").split(",")]
    cashes = await get_cashes(message.text, f_vers)
    clients = await db.get_clients_by_shopcodes([c.shopcode for c in cashes])
    text = (
        f"{texts.information_head}"
        f"- Найденно касс: {len(cashes)}\n"
        f"- Найденно клиентов с данными кассами: {len(clients)}\n"
    )
    await state.update_data(filter_create_post=message.text)
    await message.answer(text, reply_markup=inline.kb_send_post_filter_continue())


@router.callback_query(F.data == "send_post_filter_continue")
async def send_post_filter_continue(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    log_e.button("Продолжить рассылку по фильтру")
    await call.message.edit_text(
        "Отправьте сообщение. В сообщение должно быть максимум 1 картинка"
    )
    await state.set_state(CreatePostState.text_filter)


@router.message(CreatePostState.text_filter)
async def text_filter(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.info(f"Текст рекламной рассылки по фильтру '{message.text}'")
    await state.update_data(filter_create_post_msg_id=message.message_id)
    await state.set_state(CreatePostState.prepare_filter)
    await message.bot.copy_message(
        message.chat.id,
        message.from_user.id,
        message.message_id,
        reply_markup=inline.kb_send_post_filter(),
    )


@router.callback_query(F.data == "send_post_filter_accept")
async def send_post_filter_accept(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    log_e.button("Принять рекламную рассылку")
    data = await state.get_data()
    f_vers = [int(f) for f in data.get("send_post_f_vers").split(",")]
    cashes = await get_cashes(data.get("filter_create_post"), f_vers)
    clients = await db.get_clients_by_shopcodes([c.shopcode for c in cashes])
    await call.message.edit_text(
        f"Рассылка началась, она будет отправлена {len(clients)} клиентам. Ожидайте..."
    )
    count = 0
    for client in clients:
        try:
            await call.bot.copy_message(
                client.user_id, call.from_user.id, data["filter_create_post_msg_id"]
            )
            await asyncio.sleep(0.05)
            count += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except Exception as e:
            log_e.error(e)
            except_log.exception(e)
    await call.message.answer(f"Рассылка завершена. Отправлена {count} клиентам.")
