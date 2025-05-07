import asyncio
import os
from datetime import datetime
from pathlib import Path

import config
from core.database.query_PROGRESS import get_cash_info


async def get_last_file(inn: str, fsrar: str, type_file: str = "xls") -> Path | bool:
    """
    Получает инн и фсрар точки
    Возвращает путь к файлу и его в формате '%d-%m-%Y %H:%m'
    """
    dir_path = Path(config.server_path, "ostatki", inn, fsrar, type_file)
    if not dir_path.exists():
        raise FileNotFoundError("У вас отсутствуют сохранённые остатки")
    files = [
        Path(dir_path, file)
        for file in os.listdir(dir_path)
        if Path(dir_path, file).is_file()
    ]
    if not files:
        return False

    return max(files, key=os.path.getctime)


async def get_last_files(
    inn: str, fsrar: str, type_file: str = "xls"
) -> list[list[Path, str]] | bool:
    """
    Получает ИНН и ФСРАР точки
    Возвращает список [[путь к файлу, date('%d-%m-%Y %H:%m)],...]
    """
    dir_path = Path(config.server_path, "ostatki", inn, fsrar, type_file)
    if not dir_path.exists():
        raise FileNotFoundError("У вас отсутствуют сохранённые остатки")
    files = [
        Path(dir_path, file)
        for file in os.listdir(dir_path)
        if os.path.isfile(Path(dir_path, file))
    ]
    if not files:
        return False

    ostatki = sorted(files, key=os.path.getctime)
    ostatki.reverse()
    result = []
    for file in ostatki[:6]:
        ostatki_file_path = file.name.split(os.sep)[-1]
        if file.name.endswith("xlsx"):
            date_file = file.name.split(os.sep)[-1].split(".")[0]
        else:
            date_file = "__".join(file.name.split("__")[1:]).rstrip(".xml")
        date_file = datetime.strptime(date_file, "%Y_%m_%d__%H_%M").strftime(
            "%d-%m-%Y %H:%M"
        )
        result.append([ostatki_file_path, date_file])
    return result


if __name__ == "__main__":
    cash_info = get_cash_info("123")
    asyncio.run(get_last_files(cash_info.inn, cash_info.fsrar))
