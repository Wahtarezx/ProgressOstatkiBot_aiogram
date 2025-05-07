from datetime import datetime
from pathlib import Path
from typing import Tuple

from aiogram.types import Message
import pandas as pd

from core.services.egais.goods.pd_models import Product
from core.services.markirovka.enums import GroupIds
from core.services.markirovka.inventory.models import ProductVolume, CIS
from core.loggers.markirovka_logger import LoggerZnak
from core.services.markirovka.ofdplatforma import get_pg_info
from core.services.markirovka.ostatki.models import OstatkiExcel, OstatkiCSV
from core.services.markirovka.pd_models.gismt import Balance
from core.utils import texts


def parse_ostatki_csv(csv_path: Path) -> OstatkiCSV:
    code, value = read_csv_for_error(csv_path)
    excel_path = f"{csv_path}.xlsx"
    if value is not None:
        return OstatkiCSV(
            excel_path=excel_path, csv_path=csv_path, error_code=code, error_value=value
        )

    df = pd.read_csv(
        str(csv_path),
        skiprows=1,
        usecols=["requestedCis", "gtin", "productGroup", "productName"],
        na_values=["?"],
    )
    count = len(df.index)
    products = []
    for cis, gtin, name, pg_name in df.values:
        find = False
        # if pg_name.lower() != PG_NAME.lower():
        #     log = logger.bind(cis=cis, gtin=gtin, name=name, pg_name=pg_name)
        #     log_m.debug(f'Пропустил товар, он из другой товарной группы')
        #     continue
        for product in products:
            if product.gtin == f'{"0" * (14 - len(str(gtin)))}{str(gtin)}':
                find = True
                product.gtin_quantity += 1
                product.name = name
                product.cises.append(
                    CIS(name=name, cis=cis, gtin=str(gtin), pg_name=pg_name)
                )
        if not find:
            products.append(
                ProductVolume(
                    gtin=str(gtin),
                    name=name,
                    gtin_quantity=1,
                    cises=[CIS(name=name, cis=cis, gtin=str(gtin), pg_name=pg_name)],
                )
            )
    df = df.drop("gtin", axis=1)
    df = df.drop("productGroup", axis=1)
    df.columns = ["Количество", "Название"]
    df = (
        df.groupby("Название")
        .count()
        .reset_index()
        .sort_values(by=["Количество"], ascending=False)
    )
    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as wb:
        df.to_excel(wb, sheet_name="Баланс", index=False)
        sheet = wb.sheets["Баланс"]
        sheet.autofilter("A1:B" + str(df.shape[1]))
        sheet.set_column("A:A", 50)
        sheet.set_column("B:B", 15)
    return OstatkiCSV(
        excel_path=excel_path,
        csv_path=csv_path,
        count_positions=len(df.index),
        count=count,
        products=products,
    )


async def write_volume_balance(
    marks: tuple[list[tuple[Product, Balance]], GroupIds], path_to_save: Path
) -> OstatkiExcel:
    products, group_id = marks
    products_info, balance = products

    df = pd.DataFrame(
        [
            (product.name, product.gtin, balance.quantity)
            for product, balance in products_info
        ]
    )
    dir_save_path = path_to_save / group_id.name
    dir_save_path.mkdir(parents=True, exist_ok=True)
    excel_path = (
        dir_save_path
        / f'{datetime.now().strftime("%Y-%m-%d__%H_%m")}_{group_id.name}.xlsx'
    )
    # df = df[df['quantity'] > 0]
    products = []
    for name, gtin, quantity, pg_name in df.values:
        if quantity < 1:
            continue
        products.append(ProductVolume(gtin=gtin, gtin_quantity=quantity, name=name))
    df.columns = ["Название", "Штрихкод", "Количество"]
    df = df.sort_values(by=["Количество"], ascending=False)
    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as wb:
        df.to_excel(wb, sheet_name="Баланс", index=False)
        sheet = wb.sheets["Баланс"]
        sheet.autofilter("A1:C" + str(df.shape[1]))
        sheet.set_column("A:A", 50)
        sheet.set_column("B:B", 15)
        sheet.set_column("C:C", 15)
    return OstatkiExcel(
        excel_path=excel_path,
        count_positions=len(df.index),
        count=int(df["Количество"].sum()),
        products=products,
        pg_name=group_id.name,
    )


def read_csv_for_error(file_path: Path) -> tuple[int, None] | tuple[int, str]:
    df = pd.read_csv(str(file_path), nrows=4, skiprows=1, header=None)
    for i, d in enumerate(df.values):
        if d[0] == "errors":
            message = df.values[i + 1][0]
            code, value = message.split(": ")
            return int(code), str(value)
    return 0, None


async def check_excel_ostatki_files_for_errors(
    message: Message, excel_files: list[OstatkiExcel], log_m: LoggerZnak
) -> list[OstatkiExcel]:
    result = []
    for e_file in excel_files:
        text_info = (
            f"<b>Товарная группа</b>: {e_file.pg_name}\n"
            f"<b>Позиций</b>: {e_file.count_positions}\n"
        )
        if e_file.error_code != 0 and e_file.error_value is not None:
            text = f"{texts.intersum_head}"
            if e_file.error_code == 10:
                text += "<b><u>Не подписан договор</u></b>\n"
            elif e_file.error_code == 5:
                text += "<b><u>Пустые остатки</u></b>\n"
            else:
                text += f"<b><u>{e_file.error_value}</u></b>\n"
            text += f"{text_info}"
            log_m.error(e_file.error_value)
            await message.answer(text)
        else:
            result.append(e_file)
    return result


async def products_to_excel(products: list[ProductVolume]):
    df = pd.DataFrame(*products)
    print(df)


if __name__ == "__main__":
    # print(read_csv_for_error(r'C:\Users\User\AppData\Roaming\MobaXterm\slash\RemoteFiles\132066_2_74\file-95f76dc2-b320-4cbb-8078-c5afca47355b.csv'))
    # print(read_csv_for_error(r'C:\Users\User\AppData\Roaming\MobaXterm\slash\RemoteFiles\132066_2_72\file-05158a82-7be3-4372-b584-5235a4e87b7b.csv'))
    # print('(01)4606203098910(21)a/sDMCw'.replace('(21)', '').replace('(01)', ''))
    file = parse_ostatki_csv(
        r"C:\Users\User\Desktop\file-85757e71-bb39-40e9-a23a-4b5423ec9c6f.csv"
    )
    with open("cises.txt", "w+") as f:
        for p in file.products:
            for c in p.cises:
                f.write(f"{c.cis}\n")
