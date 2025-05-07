import os.path

import config
from core.cron.datastudio.Spreadsheet import Spreadsheet
import asyncio
from datetime import datetime

from core.database.query_BOT import (
    get_ttn_log,
    get_ostatki_log,
    get_goods_log,
    get_inventory_log,
)
from core.database.query_PROGRESS import (
    get_shipper_info,
    check_cash_info,
    get_cash_info,
)
from core.utils.foreman.foreman import get_cash


async def logs_ttn(path):
    ss = Spreadsheet(path, "logs_ttn", spreadsheetId=config.logs_sheet_id)
    last_row = ss.get_last_cell_in_column("A") - 1
    logs = await get_ttn_log(last_row)
    for count, log in enumerate(logs, start=last_row + 2):
        shipper = get_shipper_info(inn=log.shipper_inn)
        cash_number = (
            log.cash_number.split("-")[1] if "-" in log.cash_number else log.cash_number
        )
        cash = await get_cash(cash_number)
        description = "-" if log.description is None else log.description
        if cash is not None and shipper is not None:
            ss.prepare_setValues(
                f"A{count}:F{count}",
                [
                    [
                        log.date.strftime("%Y-%m-%d"),
                        str(cash_number),
                        str(log.type),
                        str(cash.artix_shopname),
                        str(shipper.name),
                        str(description),
                    ]
                ],
            )
        if count % 50 == 0:
            ss.runPrepared()
    ss.runPrepared()


async def logs_ostatki(path):
    ss = Spreadsheet(path, "logs_ostatki", spreadsheetId=config.logs_sheet_id)
    last_row = ss.get_last_cell_in_column("A") - 1
    logs = await get_ostatki_log(last_row)
    for count, log in enumerate(logs, start=last_row + 2):
        cash_number = (
            log.cash_number.split("-")[1] if "-" in log.cash_number else log.cash_number
        )
        cash = await get_cash(cash_number)
        ss.prepare_setValues(
            f"A{count}:C{count}",
            [
                [
                    log.date.strftime("%Y-%m-%d"),
                    str(cash_number),
                    cash.artix_shopname,
                ]
            ],
        )
        if count % 50 == 0:
            ss.runPrepared()
    ss.runPrepared()


async def logs_goods(path):
    ss = Spreadsheet(path, "logs_goods", spreadsheetId=config.logs_sheet_id)
    last_row = ss.get_last_cell_in_column("A") - 1
    logs = await get_goods_log(last_row)
    for count, log in enumerate(logs, start=last_row + 2):
        cash_number = (
            log.cash_number.split("-")[1] if "-" in log.cash_number else log.cash_number
        )
        cash = await get_cash(cash_number)
        description = "-" if log.description is None else log.description
        ss.prepare_setValues(
            f"A{count}:I{count}",
            [
                [
                    log.date.strftime("%Y-%m-%d"),
                    str(cash_number),
                    str(log.type),
                    str(cash.artix_shopname),
                    str(log.bcode),
                    str(log.op_mode),
                    str(log.otdel),
                    str(log.price),
                    str(description),
                ]
            ],
        )
        if count % 50 == 0:
            ss.runPrepared()
    ss.runPrepared()


async def logs_inventory(path):
    ss = Spreadsheet(path, "logs_inventory", spreadsheetId=config.logs_sheet_id)
    last_row = ss.get_last_cell_in_column("A") - 1
    logs = await get_inventory_log(last_row)
    for count, log in enumerate(logs, start=last_row + 2):
        cash_number = (
            log.cash_number.split("-")[1] if "-" in log.cash_number else log.cash_number
        )
        cash = await get_cash(cash_number)
        description = "-" if log.description is None else log.description
        ss.prepare_setValues(
            f"A{count}:F{count}",
            [
                [
                    log.date.strftime("%Y-%m-%d"),
                    str(cash_number),
                    str(cash.artix_shopname),
                    str(log.phone),
                    str(log.count_bottles),
                    str(description),
                ]
            ],
        )
        if count % 50 == 0:
            ss.runPrepared()
    ss.runPrepared()


async def main_logs(
    path=os.path.join(config.dir_path, "core", "cron", "datastudio", "pythonapp.json")
):
    await logs_ttn(path)
    await logs_ostatki(path)
    await logs_goods(path)
    await logs_inventory(path)


if __name__ == "__main__":
    asyncio.run(main_logs())
