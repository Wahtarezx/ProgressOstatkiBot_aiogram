from datetime import datetime, timedelta, date
from pathlib import Path

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

import config
from core.loggers.egais_logger import LoggerEGAIS
from core.utils import texts
from core.utils.cash_sales.sales import CashSales
from core.utils.foreman.pd_model import ForemanCash
from ..callback_data import DaysHistorySales
from ..states import StateSalesPeriod
from ..to_excel import create_excel_sales

router = Router()


@router.callback_query(DaysHistorySales.filter())
async def select_days_sales(
    call: CallbackQuery,
    log_e: LoggerEGAIS,
    callback_data: DaysHistorySales,
    state: FSMContext,
):
    await call.message.answer(texts.load_information)
    log_e.button(f"Выбор периода за последние {callback_data.days} дней")
    start_date = datetime.date(datetime.now()) - timedelta(days=callback_data.days)
    end_date = datetime.date(datetime.now())
    log_e.debug(f"Период с {start_date} по {end_date}")
    data = await state.get_data()
    foreman_cash = ForemanCash.model_validate_json(data["foreman_cash"])
    dir_sales = Path(
        config.server_path,
        "backup",
        "sales",
        str(foreman_cash.shopcode),
        str(foreman_cash.cashcode),
    )
    cash_sales = CashSales(dir_sales)
    shifts = await cash_sales.get_sales(start_date, end_date)
    if not shifts or len(shifts.shifts) == 0:
        await call.message.answer(texts.no_sales)
        return
    excel_file = await create_excel_sales(shifts, foreman_cash, start_date, end_date)
    await call.message.bot.send_document(call.message.chat.id, FSInputFile(excel_file))


@router.callback_query(F.data == "enter_period_sales")
async def start_enter_period_sales(
    call: CallbackQuery, log_e: LoggerEGAIS, state: FSMContext
):
    log_e.button("Написать период самому")
    log_e.debug("Напишите ответным сообщением дату с какого числа начать поиск продаж")
    await call.message.edit_text(
        "Напишите ответным сообщением дату с какого числа начать поиск продаж\n"
        "Например: 01.01.2024"
    )
    await state.set_state(StateSalesPeriod.start_date)


@router.message(StateSalesPeriod.start_date)
async def end_enter_period_sales(
    message: Message, state: FSMContext, log_e: LoggerEGAIS
):
    log_e.info(f'Написали дату с "{message.text}"')
    try:
        start_date = datetime.strptime(message.text, "%d.%m.%Y")
    except Exception:
        log_e.error(f'Неправильно написана дата "{message.text}"')
        await message.answer(
            texts.error_head + "Неправильно написана дата\n"
            "Напишите ответным сообщением дату с какого числа начать поиск\n"
            "Например: 01.01.2024"
        )
        return
    await state.update_data(sales_start_date=message.text)
    log_e.debug("Напишите ответным сообщением дату по какое число искать продажи")
    await message.answer(
        "Напишите ответным сообщением дату по какое число искать продажи\n"
        "Например: 01.01.2024"
    )
    await state.set_state(StateSalesPeriod.end_date)


@router.message(StateSalesPeriod.end_date)
async def finish(message: Message, state: FSMContext, log_e: LoggerEGAIS):
    log_e.info(f'Написали дату по "{message.text}"')
    try:
        end_date = datetime.strptime(message.text, "%d.%m.%Y")
    except Exception:
        log_e.error(f'Неправильно написана дата "{message.text}"')
        await message.answer(
            texts.error_head + "Неправильно написана дата\n"
            "Напишите ответным сообщением дату по какое число искать продажи\n"
            "Например: 01.01.2024"
        )
        return
    data = await state.get_data()
    start_date = datetime.strptime(data["sales_start_date"], "%d.%m.%Y")

    start_date = date(start_date.year, start_date.month, start_date.day)
    end_date = date(end_date.year, end_date.month, end_date.day)
    await message.answer(texts.load_information)
    foreman_cash = ForemanCash.model_validate_json(data["foreman_cash"])
    dir_sales = Path(
        config.server_path,
        "backup",
        "sales",
        str(foreman_cash.shopcode),
        str(foreman_cash.cashcode),
    )
    cash_sales = CashSales(dir_sales)
    shifts = await cash_sales.get_sales(start_date, end_date)
    if not shifts or len(shifts.shifts) == 0:
        await message.answer(texts.no_sales)
        return
    excel_file = await create_excel_sales(shifts, foreman_cash, start_date, end_date)
    await message.bot.send_document(message.chat.id, FSInputFile(excel_file))
    await state.set_state(StateSalesPeriod.finish)
