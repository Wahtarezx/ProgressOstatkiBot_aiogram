from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from core.database.query_BOT import add_artix_autologin, add_referrals, Database
from core.handlers.basic import get_start
from core.keyboards.reply import getKeyboard_registration
from core.loggers.egais_logger import LoggerEGAIS
from core.utils import texts
from core.utils.foreman.pd_model import ForemanCash, Deeplink

db = Database()


async def get_true_contact(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    phone = texts.phone(message.contact.phone_number)
    chat_id = message.chat.id
    first_name = message.contact.first_name
    last_name = message.contact.last_name
    user_id = message.contact.user_id
    q = await db.get_client_info(user_id=message.from_user.id)
    if not q:
        await db.update_client_info(
            phone_number=phone,
            chat_id=chat_id,
            first_name=first_name,
            last_name=last_name,
            user_id=user_id,
        )
        data = await state.get_data()
        if data.get("deeplink_foreman_cash") is not None:
            cash = ForemanCash.model_validate_json(data["deeplink_foreman_cash"])
            deeplink = Deeplink.model_validate_json(data["deeplink"])
            await add_artix_autologin(cash, message.chat.id)
            await add_referrals(
                deeplink.ref_id,
                str(message.chat.id),
                deeplink.shopcode,
                deeplink.cashcode,
            )
            await state.update_data(deeplink_foreman_cash=None, deeplink=None)
        await message.answer(
            texts.success_head + texts.succes_registration,
            reply_markup=ReplyKeyboardRemove(),
        )
        await get_start(message, state, log_e)
    else:
        await get_start(message, state, log_e)


async def get_fake_contact(message: Message, log_e: LoggerEGAIS):
    phone = texts.phone(message.contact.phone_number)
    log_e.error(f'Отправили чужой сотовый "{phone}"')
    await message.answer(
        texts.error_fake_client_phone,
        reply_markup=getKeyboard_registration(),
        parse_mode="HTML",
    )
