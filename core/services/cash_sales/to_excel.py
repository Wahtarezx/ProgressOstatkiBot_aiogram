from datetime import datetime, date
from pathlib import Path
from typing import Generator

import pandas as pd

import config
from core.database.models_enum import Roles
from core.loggers.make_loggers import bot_log
from core.utils.cash_sales.pd_model import CashShifts
from core.utils.foreman.pd_model import ForemanCash


def data_for_df(
    cash_shifts: CashShifts, foreman_cash: ForemanCash
) -> Generator[dict, None, None]:
    for shift in cash_shifts.shifts:
        for check in shift.checks:
            if check.docType == 1:
                doc_type = "Продажа"
            elif check.docType == 2:
                doc_type = "Возврат"
            elif check.docType == 3:
                doc_type = "Внесение"
            elif check.docType == 4:
                doc_type = "Выем"
            elif check.docType == 7:
                doc_type = "Аннулирование продажи"
            elif check.docType == 8:
                doc_type = "Аннулирование возврата"
            elif check.docType == 13:
                doc_type = "Остаток денег на начало смены"
            elif check.docType == 16:
                doc_type = "Документ инвентаризации"
            elif check.docType == 18:
                doc_type = "Возврат поставщику"
            elif check.docType == 25:
                doc_type = "Возврат по чеку продажи"
            elif check.docType == 29:
                doc_type = "Постановка кега на кран"
            elif check.docType == 30:
                doc_type = "Отключение кега от крана"
            else:
                doc_type = "Прочие"
            for position in check.inventPositions:
                if position.deptCode == 1:
                    dcode = "Алкоголь"
                elif position.deptCode == 2:
                    dcode = "Пиво"
                elif position.deptCode == 3:
                    dcode = "Сигареты"
                elif position.deptCode == 4:
                    dcode = "Продукты"
                elif position.deptCode == 5:
                    dcode = "Маркированный товар"
                elif position.deptCode == 6:
                    dcode = "Маркированный товар"
                else:
                    dcode = "Прочие"
                yield {
                    "№ Чека": check.docNum,
                    "№ Смены": shift.shift.shift,
                    "Кассир": [
                        user.username
                        for user in shift.shift.users
                        if user.usercode == position.userCode
                    ][0],
                    "Наименование": position.name,
                    "Штрихкод": position.barCode,
                    "Количество": position.quant,
                    "Цена": position.price,
                    "Сумма": position.sume,
                    "Отдел": dcode,
                    "Юр. лицо": (
                        foreman_cash.artix_shopname
                        if str(position.deptCode)
                        in foreman_cash.kkm1_departs.split(",")
                        else foreman_cash.artix_shopname2
                    ),
                    "Тип оплаты": check.moneyPositions[0].valName,
                    "Сумма оплаты": check.moneyPositions[0].sume,
                    "Время закрытия чека": check.timeEnd,
                    "Тип документа": doc_type,
                    "Акц.Марка\Маркировка": position.excisemark,
                }


async def write_to_excel(path_file: Path, df: pd.DataFrame):
    # Записываем данные в Excel с использованием XlsxWriter
    with pd.ExcelWriter(path_file, engine="xlsxwriter") as writer:
        sheet_name = "info"
        df.to_excel(writer, sheet_name=sheet_name, index=False, na_rep="NaN")

        # Определяем рабочий лист
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        # Устанавливаем автофильтр на диапазон данных
        max_row, max_col = df.shape
        worksheet.autofilter(0, 0, max_row, max_col - 1)

        # Устанавливаем ширину колонок на основе максимальной длины данных
        for i, column in enumerate(df.columns):
            column_length = max(df[column].astype(str).map(len).max(), len(column))
            worksheet.set_column(i, i, column_length + 3)

        # Определяем формат для итоговой строки
        total_format = workbook.add_format({"bold": True, "bg_color": "#F9F9F9"})

        # Добавляем итоговую строку
        total_row = max_row + 1  # Индексация строк начинается с 0

        worksheet.write(total_row, 0, "Итого:", total_format)

        # Определяем индексы столбцов для суммирования
        sum_columns = {
            # 'Количество': df.columns.get_loc('Количество'),
            # 'Цена': df.columns.get_loc('Цена'),
            "Сумма": df.columns.get_loc("Сумма"),
            # 'Сумма оплаты': df.columns.get_loc('Сумма оплаты')
        }

        for col_name, col_idx in sum_columns.items():
            # Преобразуем индексы в формат Excel (A, B, C, ...)
            excel_col = chr(65 + col_idx)
            # Записываем формулу суммирования
            formula = f"=SUM({excel_col}2:{excel_col}{max_row +1})"
            worksheet.write_formula(total_row, col_idx, formula, total_format)

        # Дополнительно можно добавить границу выше итоговой строки
        border_format = workbook.add_format({"top": 1})
        worksheet.set_row(total_row, None, border_format)


def get_latest_file_in_directory(directory_path: Path, role: Roles) -> Path:
    # Получаем список всех файлов в директории
    files = [f for f in directory_path.iterdir() if f.is_file() and role.name in f.name]

    # Если в директории есть файлы
    if files:
        # Сортируем файлы по времени создания (от последнего к первому)
        latest_file = max(files, key=lambda f: f.stat().st_ctime)
        return latest_file
    else:
        return None


async def create_excel_sales(
    sales: CashShifts, foreman_cash: ForemanCash, start_date: date, end_date: date
) -> Path:
    # Путь для сохранения файла
    dir_path = Path(
        config.dir_path,
        "files",
        "sales",
        str(foreman_cash.shopcode),
        str(foreman_cash.cashcode),
    )
    dir_path.mkdir(parents=True, exist_ok=True)
    path_file = (
        dir_path
        / f"{datetime.now().strftime(f'comp{foreman_cash.shopcode}_{start_date}__{end_date}')}.xlsx"
    )
    if path_file.exists():
        path_file.unlink()

    df = pd.DataFrame(data_for_df(sales, foreman_cash))
    end_time_check = df["Время закрытия чека"].to_list()
    if end_time_check:
        df = df.sort_values(by="Время закрытия чека", ascending=True)

    await write_to_excel(path_file, df)

    return path_file
