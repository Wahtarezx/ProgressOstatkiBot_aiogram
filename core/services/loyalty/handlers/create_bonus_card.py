import re
import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from core.loggers.egais_logger import LoggerEGAIS
from core.services.loyalty.keyboards import inline
from core.utils import texts
from core.utils.CS.cs import CS
from core.utils.CS.pd_model import CardInfo, Client
from core.utils.states import Menu
from ..states import CreateBonusCardState

router = Router()


@router.callback_query(F.data == "create_bonus_card")
async def start_loyalty_system(
    call: CallbackQuery, log_e: LoggerEGAIS, state: FSMContext
):
    log_e.button("Добавить бонусную карту")
    await call.message.edit_text(
        "Напишите ответным сообщением <b>сотовый</b> клиента\n" "Например: 79961234567"
    )
    await state.set_state(CreateBonusCardState.phone)
    await state.update_data(create_bonus_card_cardnumber=None)


@router.message(CreateBonusCardState.phone)
async def accept_phone(message: Message, log_e: LoggerEGAIS, state: FSMContext):
    log_e.info(f"Ввели сотовый клиента: {message.text}")
    phone: str = re.findall(r"[0-9]+", message.text)[0]
    if len(phone) != 11:
        log_e.error("Сотовый должен состоять из 11 цифр.")
        await message.answer(
            "Сотовый должен состоять из 11 цифр.\n"
            "Напишите еще раз ответным сообщение сотовый клиента"
        )
        return

    correct_phone = "7" + phone[1:] if phone.startswith("8") else phone
    cs = CS()
    client = await cs.get_client_by_phonenubmer(correct_phone)
    if client.get("number") is not None:
        log_e.error("Данный клиент уже создан")
        await message.answer(texts.error_head + "Данный клиент уже создан")
        return
    await state.update_data(create_bonus_card_phone=correct_phone)
    await state.set_state(CreateBonusCardState.number_card)
    await message.answer(
        "Напишите ответным сообщением <b>номер карты</b> клиента\n"
        "Например: 100001123123",
        reply_markup=inline.kb_skip_number_card(),
    )


@router.message(CreateBonusCardState.number_card)
async def accept_number_card(message: Message, log_e: LoggerEGAIS, state: FSMContext):
    log_e.info(f"Написали номер карты: {message.text}")
    cs = CS()
    client = await cs.get_card_by_id(message.text)
    if client is not None:
        await message.answer(
            texts.error_head + f"Клиент с данной картой уэе зарегистрирован\n"
            f"Напишите ответным сообщением другой номер карты.",
            reply_markup=inline.kb_skip_number_card(),
        )
        return
    await state.update_data(create_bonus_card_cardnumber=message.text)
    await state.set_state(CreateBonusCardState.fio)
    await message.answer(
        "Напишите ответным сообщением <b>имя</b> клиента\n" "Например: Илья"
    )


@router.callback_query(F.data == "create_bonus_card_skip_cardbonus")
async def skip_cardnumber(call: CallbackQuery, log_e: LoggerEGAIS, state: FSMContext):
    log_e.button("Пропустить ввод номера карты")
    await state.set_state(CreateBonusCardState.fio)
    await call.message.edit_text(
        "Напишите ответным сообщением <b>имя</b> клиента\n" "Например: Илья"
    )


@router.message(CreateBonusCardState.fio)
async def accept_name(message: Message, log_e: LoggerEGAIS, state: FSMContext):
    log_e.info(f"Написали имя клиента: {message.text}")
    data = await state.get_data()

    cs = CS()
    card_number = (
        str(uuid.uuid4())
        if data.get("create_bonus_card_cardnumber") is None
        else data.get("create_bonus_card_cardnumber")
    )
    await cs.create_client(
        Client(
            idclient=card_number,
            phonenumber=data.get("create_bonus_card_phone"),
            name=message.text,
        ),
    )
    await cs.create_card(
        CardInfo(idcard=card_number, number=card_number, idclient=card_number),
    )
    await message.answer(
        texts.success_head + f"Клиент успешно создан\n"
        f"Имя: {message.text}\n"
        f"Номер карты: {card_number}\n"
        f"Сотовый: {data.get('create_bonus_card_phone')}",
    )
    await state.set_state(Menu.menu)
