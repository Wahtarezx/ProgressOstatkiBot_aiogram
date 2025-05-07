import asyncio
import os

from aiogram.filters import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.deep_linking import create_start_link
from aiogram.utils.payload import decode_payload

import config
from core.database import query_BOT
from core.database.modelBOT import Clients
from core.database.models_enum import Roles
from core.database.query_BOT import add_artix_autologin, Database
from core.keyboards import inline
from core.keyboards import reply
from core.loggers.egais_logger import LoggerEGAIS
from core.services.edo.schemas.login.models import EnumEdoProvider
from core.services.egais.logins.pd_models import Client
from core.services.markirovka.trueapi import main3, TrueApi
from core.utils import texts
from core.utils.edo_providers.edo_lite.model import EdoLite
from core.utils.edo_providers.factory import EDOFactory
from core.utils.foreman import foreman
from core.utils.foreman.foreman import get_cash
from core.utils.foreman.pd_model import ForemanCash, Deeplink
from core.utils.redis import RedisConnection
from core.utils.states import Menu, Auth, RefState, TestState

db = Database()


async def check_reg(
    message: Message, state: FSMContext, log_e: LoggerEGAIS
) -> Clients | None:
    client_db = await query_BOT.get_client_info(message.chat.id)
    if not client_db:  # Нужно пройти регистрацию
        log_e.error("Нужно пройти регистрацию")
        await message.bot.send_video(
            message.chat.id,
            FSInputFile(
                os.path.join(config.dir_path, "files", "tutorial_registration.mp4")
            ),
            reply_markup=reply.getKeyboard_registration(),
        )
        await message.answer(
            texts.need_registration, reply_markup=reply.getKeyboard_registration()
        )
        return

    if len(client_db.autologins) == 0:  # Нужно пройти авторизацию
        await message.answer(
            texts.auth_head + "Напишите ответным сообщением номер вашего компьютера"
        )
        await state.set_state(Auth.send_cash_number)
        return

    return client_db


async def update_cash_info(
    message: Message, state: FSMContext, log_e: LoggerEGAIS
) -> None:
    data = await state.get_data()
    if data.get("foreman_cash") is not None:
        old_cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
        new_cash = await foreman.get_cash(
            f"cash-{old_cash.shopcode}-{old_cash.cashcode}"
        )
        log_e.debug(new_cash.model_dump_json())
    client_db = await query_BOT.get_client_info(message.chat.id)
    client = Client(
        date=client_db.date,
        phone_number=client_db.phone_number,
        first_name=client_db.first_name,
        last_name=client_db.last_name,
        user_id=client_db.user_id,
        chat_id=client_db.chat_id,
        cash=client_db.cash,
        admin=client_db.admin,
        whitelist_admin=client_db.whitelist_admin,
        accept_admin=client_db.accept_admin,
        edo_admin=client_db.edo_admin,
        autologins=[_.__dict__ for _ in client_db.autologins],
    ).model_dump_json()
    if data.get("foreman_cash") is not None:
        await state.update_data(
            foreman_cash=new_cash.model_dump_json(by_alias=True), client=client
        )
    else:
        await state.update_data(client=client)


async def get_start(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("/start")
    data = await state.get_data()
    await state.update_data(user_id=message.from_user.id)
    if data.get("foreman_cash") is None:
        await cc(message, state, log_e)
        return
    client = await check_reg(message, state, log_e)
    if not client:
        return
    await update_cash_info(message, state, log_e)
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    msg = texts.information_head
    msg += f"<b>Номер компьютера</b>: <code>{cash.shopcode}-{cash.cashcode}</code>\n"
    msg += f"<b>Адрес</b>: <code>{cash.address}</code>\n\n"
    full_text, error_messages = await texts.profile(cash=cash)
    msg += error_messages
    await message.answer(msg, reply_markup=inline.kb_startMenu(cash))
    await state.set_state(Menu.menu)


async def cc(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("/comp")
    client = await check_reg(message, state, log_e)
    if not client:
        return
    await message.answer(
        "Выберите нужный номер компьютера", reply_markup=inline.kb_changeComp(client)
    )


async def auth_cash_number(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.info(f'Напечатали номер компьютера "{message.text}"')

    if message.text is None:
        await message.answer(
            texts.error_head + "Напишите только номер компьютера\nНапример: 887"
        )
        return
    if not message.text.isdigit():
        await message.answer(
            texts.error_head + "Напишите только номер компьютера\nНапример: 887"
        )
        return

    client_db = await db.get_client_info(user_id=message.from_user.id)
    if message.text in [
        str(_.shopcode) for _ in await db.get_autologin_cashes(message.from_user.id)
    ]:
        log_e.info(
            f'Напечатали номер компьютера который уже добавлен "{message.text}". Перевёл в меню /comp'
        )
        await cc(message, state, log_e)
    cash = await foreman.get_cash(f"cash-{message.text}-")
    await state.update_data(foreman_cash=cash.model_dump_json(by_alias=True))

    role = Roles(client_db.role.role)
    if (
        role in [Roles.ADMIN, Roles.TEHPOD]
        or role == Roles.SAMAN_PROVIDER
        and cash.inn in config.SAMAN_INNS
        or role == Roles.PREMIER_PROVIDER
        and cash.inn in config.PREMIER_INNS
        or role == Roles.ROSSICH_PROVIDER
        and cash.inn in config.ROSSICH_INNS
    ):
        await add_artix_autologin(cash, message.chat.id)
        await get_start(message, state, log_e)
        return

    await state.set_state(Auth.send_password)
    await message.answer(
        texts.auth_head
        + "Напишите ответным сообщением ИНН вашего ООО или ИНН вашего ИП"
    )


async def auth_password(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    password = message.text
    log_e.info(f'Напечатали пароль "{password}"')
    if password == cash.inn or password == cash.inn2:
        log_e.success(f"Пароль верен")
        await add_artix_autologin(cash, message.chat.id)
        await get_start(message, state, log_e)
    else:
        log_e.error("Неверный пароль")
        await message.answer(
            texts.error_head + "Вы ввели неверный ИНН\nПопробуйте снова."
        )


async def from_oldBot(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    log_e.info("Зашел со старого бота")
    await get_start(call.message, state, log_e)


async def callback_get_start(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    log_e.button("Главное меню из профиля")
    await get_start(call.message, state, log_e)
    await call.answer()


async def my_id(message: Message):
    await message.answer(f"Ваш ID: <code>{message.chat.id}</code>")


async def clear(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    await state.clear()
    log_e.button("/clear")
    await message.answer("Кэш успешно очищен✅")
    await cc(message, state, log_e)


async def test(
    message: Message,
    state: FSMContext,
    log_e: LoggerEGAIS,
    redis_connection: RedisConnection,
    edo_factory: EDOFactory,
):
    msg = await message.answer('test')
    await asyncio.sleep(1)
    await msg.delete()
    # trueapi = TrueApi(inn_to_auth="160502035960")
    # await trueapi.load_from_redis(redis_connection)
    # edo = await edo_factory.create_edo_operator(EnumEdoProvider.edolite)
    # print(await edo.get_documents_for_accept())
    # await edo.save_to_redis(redis_connection)
    # edolite = await EdoLite.load_from_redis(redis_connection)
    # print(await edolite.get_documents_for_accept())

    #
    # await t.create_token()
    # await state.update_data(await t.save_to_redis())
    # data = await state.get_data()
    # trueapi = await TrueApi.load_from_redis(data)
    # await message.answer(trueapi.token)
    #
    # log_e.button('/test')
    # znak = Znak(thumbprint=config.main_thumbprint, inn_to_auth='164300022229')
    # doc = znak.wait_gisMt_response('1dbd4954-9130-48d2-97f6-95ff1fc2e0a2123')
    # await message.answer(doc.model_dump_json())
    #
    # await message.answer(**as_list(
    #     texts.error_head,
    #     "\"<>\'\"?!",
    #     as_marked_section(
    #         texts.information_head.strip(),
    #         as_key_value('Название', Code('Текст')),
    #         as_key_value('Значение', Code('Текст')),
    #         marker='➖'
    #     ),
    #     Italic('Italic'),
    #     Underline('Underline'),
    #     Strikethrough('Strikethrough'),
    #     Spoiler('Spoiler'),
    #     Code('Code'),
    # ).as_kwargs())


async def url(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("/url")
    await state.set_state(TestState.uuid)
    await message.answer("uuid запроса")


async def url2(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.info(message.text)
    await main3(message.text)


async def deeplink_start(
    message: Message, command: CommandObject, state: FSMContext, log_e: LoggerEGAIS
):
    deeplink_args = decode_payload(command.args)
    log_e.info(f'deeplink_start "{deeplink_args}"')
    shopcode, cashcode, ref_id = deeplink_args.split("/")
    deeplink = Deeplink(shopcode=shopcode, cashcode=cashcode, ref_id=ref_id)
    cash = await get_cash(f"cash-{shopcode}-{cashcode}")
    await state.update_data(
        deeplink_foreman_cash=cash.model_dump_json(by_alias=True),
        deeplink=deeplink.model_dump_json(),
    )

    await get_start(message, state, log_e)


async def ref(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.button("/ref")
    await message.answer(
        "Напишите номер компьютер и номер кассы в ответ\n" "Пример: 887-1"
    )
    await state.set_state(RefState.enter_cashNumber)


async def ref_cashnumber(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.info(f'Напечатали номер компьютера "{message.text}"')
    cash = await get_cash(f"cash-{message.text}")
    link = await create_start_link(
        message.bot, cash.ref_payload(str(message.from_user.id)), encode=True
    )
    await message.answer(link)
