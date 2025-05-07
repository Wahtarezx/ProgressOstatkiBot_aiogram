from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from core.loggers.egais_logger import LoggerEGAIS
from core.utils.foreman.foreman import get_cash
from ..callback_data import DeleteCashFromAcceptlist
from ..keyboards.inline import (
    kb_acceptTTN_admin,
    kb_acceptTTN_choose_inn,
    kb_delete_cash_from_acceptlist,
)
from ..states import AddCashAcceptlist
from core.utils import texts
from core.database.query_BOT import Database

router = Router()
db = Database()


@router.callback_query(F.data == "acceptTTN_admin")
async def acceptTTN_admin(call: CallbackQuery, log_e: LoggerEGAIS):
    log_e.button("Приём без сканирования")
    text = "<b><u>Список компьютеров которые могут принимать накладные без сканирования</u></b>\n"
    text += " ".join(
        [i.cash_number.lstrip("cash-") for i in await db.get_cash_in_acceptlist()]
    )
    await call.message.edit_text(text, reply_markup=kb_acceptTTN_admin())


@router.callback_query(F.data == "add_in_acceptTTN_list")
async def start_add_cash_in_acceptlist(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    log_e.button(f"Добавить в список приёма без сканирования")
    await call.message.edit_text(texts.enter_cash_number)
    await state.set_state(AddCashAcceptlist.enter_cashNumber)


@router.message(AddCashAcceptlist.enter_cashNumber)
async def end_add_cash_in_Acceptlist(
    message: Message, state: FSMContext, log_e: LoggerEGAIS
):
    log_e.info(f'Напечатали номер компьютера "{message.text}"')
    cash = await get_cash(f"cash-{message.text}-")
    await state.update_data(acceptTTN_cash=f"cash-{cash.shopcode}-{cash.cashcode}")
    await message.answer("Выберите действие", reply_markup=kb_acceptTTN_choose_inn())


@router.callback_query(F.data == "acceptTNN_all")
async def acceptTTN_choose_all(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    data = await state.get_data()
    cash = data.get("acceptTTN_cash")
    foreman_cash = await get_cash(cash)
    await db.add_cash_in_acceptlist(
        cash_number=cash,
        inn=foreman_cash.inn,
        kpp=foreman_cash.kpp,
        accept_all_inn=True,
        may_accept_inn=None,
    )
    await call.message.edit_text(f"Компьютер <b>{cash}</b> успешно добавлен")
    log_e.success(f'Комп добавлен "{cash}"')


@router.callback_query(F.data == "acceptTNN_select")
async def acceptTTN_choose_enter_inn(
    call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS
):
    log_e.button("Ввести ИНН поставщиков")
    await call.message.edit_text(
        "Введите через пробел список ИНН поставщиков который можно будет принимать клиенту.\n"
        "Например: 1659091192 1659083875\n"
        "Например: 1659091192\n"
    )
    await state.set_state(AddCashAcceptlist.enter_inn)


@router.message(AddCashAcceptlist.enter_inn)
async def acceptTTN_enter_inn(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    cash = data.get("acceptTTN_cash")
    inns = message.text.split()
    foreman_cash = await get_cash(cash)

    for inn in inns:
        if not inn.isdigit():
            await message.answer("ИНН должен состоять только из цифр")
            return
    await db.add_cash_in_acceptlist(
        cash_number=cash,
        inn=foreman_cash.inn,
        kpp=foreman_cash.kpp,
        accept_all_inn=False,
        may_accept_inn=inns,
    )
    await message.answer(
        f'Компьютер <b>{cash}</b> успешно добавлен и ему можно принимать только {", ".join(inns)}'
    )
    log_e.success(f'Комп добавлен "{cash}"')


@router.callback_query(F.data == "remove_from_acceptTTN_list")
async def start_delete_cash_from_acceptlist(call: CallbackQuery, log_e: LoggerEGAIS):
    log_e.button(f"Удалить из приёма без сканирования")
    cashes = await db.get_cash_in_acceptlist()
    await call.message.edit_text(
        "Выберите компьютер", reply_markup=await kb_delete_cash_from_acceptlist(cashes)
    )


@router.callback_query(DeleteCashFromAcceptlist.filter())
async def delete_from_acceptlist(
    call: CallbackQuery, callback_data: DeleteCashFromAcceptlist, log_e: LoggerEGAIS
):
    await db.delete_cash_from_acceptlist(callback_data.cash)
    await call.message.edit_text(
        f'Комп "{callback_data.cash.split("-")[1]}" успешно удалён'
    )
    log_e.success(f'Комп "{callback_data.cash}" успешно удалён')
