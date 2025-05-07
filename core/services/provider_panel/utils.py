from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator

import pandas as pd
from packaging.version import Version

import config
from core.database.models_enum import Roles
from core.utils.foreman.foreman import get_info_from_all_cashes_by_inn
from core.utils.foreman.pd_model import ForemanCash


def data_for_df(cashes: list[ForemanCash]) -> Generator[dict, None, None]:
    for cash in cashes:

        if (
            (cash.kkm1_firmware is not None)
            and (cash.kkm1_firmware != "")
            and ("." in cash.kkm1_firmware)
            and (cash.kkm1_producer != "1")
        ):
            firmware = Version(cash.kkm1_firmware)
        else:
            firmware = Version("0.0.0")

        if cash.kkm1_fn_date_end:
            fn_date_end = datetime.strptime(cash.kkm1_fn_date_end, "%d.%m.%Y")
            if fn_date_end < datetime.now() - timedelta(days=420):
                continue
        if (
            (
                cash.kkm1_producer == "5"
                and firmware < Version("665.3")
                and cash.kkm1_ffd_version == "1.2"
            )
            or (
                cash.kkm1_firmware.startswith("5.")
                and cash.kkm1_producer == "4"
                and firmware < Version("5.8")
            )
            or (
                cash.kkm1_firmware.startswith("3.")
                and cash.kkm1_producer == "4"
                and firmware < Version("3.0.0.8513")
            )
            or (cash.kkm1_producer == "1")
        ):
            need_update = "Да"
        else:
            need_update = "Нет"
        artix_max_version = max(
            [Version(cash.artix_version) for cash in cashes if cash.artix_version]
        )
        need_update_artix = (
            "Да"
            if Version(cash.artix_version if cash.artix_version else "0.0.0")
            < artix_max_version
            else "Нет"
        )

        shop = {
            "Код магазина": cash.shopcode,
            "Версия Артикс": cash.artix_version,
            "Нужно обновить Артикс?": need_update_artix,
            "Код кассы": cash.cashcode,
        }
        fr1 = {
            "ФР ООО": cash.kkm1_name,
            "ЗН ФР ООО": cash.kkm1_number,
            "Прошивка ФР ООО": cash.kkm1_firmware,
            "Нужно прошивать?": need_update,
            "Соотвествие ЧЗ": "",
            "ФФД ФР ООО": cash.kkm1_ffd_version,
            "Номер ФН ФР ООО": cash.kkm1_fn_number,
            "Дата ФН ФР ООО": cash.kkm1_fn_date_end,
            "НДС ФР ООО": cash.kkm1_taxmapping,
        }

        if cash.inn in config.ROSSICH_INNS:
            if (
                (cash.kkm1_producer == "5" and firmware >= Version("665.4"))
                or (
                    cash.kkm1_firmware.startswith("5.")
                    and cash.kkm1_producer == "4"
                    and firmware >= Version("5.8")
                )
                or (
                    cash.kkm1_firmware.startswith("3.")
                    and cash.kkm1_producer == "4"
                    and firmware >= Version("3.0.0.8513")
                    or (cash.kkm1_producer == "1")
                )
                and cash.kkm1_ffd_version == "1.2"
            ):
                fr1["Соотвествие ЧЗ"] = "Да"
            else:
                fr1["Соотвествие ЧЗ"] = "Нет"
        else:
            del fr1["Соотвествие ЧЗ"]

        yield shop | fr1 | {
            # 'ФР ИП': cash.kkm2_name,
            # 'ЗН ФР ИП': cash.kkm2_number,
            # 'Прошивка ФР ИП': cash.kkm2_firmware,
            # 'ФФД ФР ИП': cash.kkm2_ffd_version,
            # 'Номер ФН ФР ИП': cash.kkm2_fn_number,
            # 'Дата ФН ФР ИП': cash.kkm2_fn_date_end,
            "Адрес": cash.address,
            "Юр.лицо": cash.artix_shopname,
            "ИНН": cash.inn,
            "КПП": cash.kpp,
            "ФСРАР": cash.fsrar,
            # 'Токен ЧЗ': cash.xapikey,
            "ИП": cash.artix_shopname2,
            "ИНН ИП": cash.inn2,
            # 'ФСРАР ИП': cash.fsrar2,
            # 'Адрес ИП': cash.address2,
            # 'Дата ГОСТ ООО Рутокен': cash.gost1_date_end,
            # 'Дата ПКИ ООО Рутокен': cash.pki1_date_end,
            #
            # 'Дата ГОСТ ИП Рутокен': cash.gost2_date_end,
            # 'Дата ПКИ ИП Рутокен': cash.pki2_date_end,
        }


async def write_to_excel(path_file: Path, df: pd.DataFrame):
    # Записываем данные в Excel с использованием XlsxWriter
    with pd.ExcelWriter(path_file, engine="xlsxwriter") as writer:
        sheet_name = "info"
        df.to_excel(writer, sheet_name=sheet_name, index=False, na_rep="NaN")

        # Определяем рабочий лист
        worksheet = writer.sheets[sheet_name]

        # Устанавливаем автофильтр на диапазон данных
        max_row, max_col = df.shape
        worksheet.autofilter(0, 0, max_row, max_col - 1)

        # Устанавливаем ширину колонок на основе максимальной длины данных
        for column in df:
            column_length = max(df[column].astype(str).map(len).max(), len(column))
            col_idx = df.columns.get_loc(column)
            worksheet.set_column(col_idx, col_idx, column_length + 3)


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


async def create_excel_analytics(inns: list[str], role: Roles) -> Path:
    # Путь для сохранения файла
    dir_path = Path(config.dir_path, "files", "providers_analytics")
    dir_path.mkdir(parents=True, exist_ok=True)
    path_file = (
        dir_path / f"{datetime.now().strftime(f'{role.name}_%Y-%m-%d_%H-%M-%S')}.xlsx"
    )

    # Проверка существования последнего файла и сколько минут назад он был создан
    last_file = get_latest_file_in_directory(dir_path, role)
    if last_file:
        file_date = last_file.name.split("_")[2:]
        file_date = "_".join(file_date).replace(".xlsx", "")
        file_creation_time = datetime.strptime(
            file_date, "%Y-%m-%d_%H-%M-%S"
        )  # Время создания файла
        if file_creation_time + timedelta(minutes=1440) > datetime.now():
            return last_file

    # Создаем DataFrame из данных
    cashes = await get_info_from_all_cashes_by_inn(inns)
    df = pd.DataFrame(data_for_df(cashes))
    df = df.sort_values(by="Прошивка ФР ООО", ascending=False)

    await write_to_excel(path_file, df)

    return path_file


if __name__ == "__main__":
    print(
        max(
            [
                Version("4.6.214"),
                Version("4.6.194"),
                Version("4.6.251"),
                Version("4.6.266"),
            ]
        )
    )
