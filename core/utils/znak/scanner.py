import re
from pathlib import Path

import cv2
from aiogram.types import Message, File
from pyzbar import pyzbar
from pylibdmtx.pylibdmtx import decode

from core.loggers.egais_logger import LoggerEGAIS
from core.loggers.markirovka_logger import LoggerZnak
from core.utils.znak.pd_model import BarcodeInfo, BarcodeType


async def get_ean_from_gtin(gtin: str):
    if gtin is not None:
        return re.findall(r"0*([0-9]+)", gtin)[0]


async def regex_check_datamatrix(cis: str) -> list[str | str] | None:
    """
    :param cis: КИ
    :return: Товарная группа маркировки, GTIN
    """
    patterns = {
        "milk8": r"\s*0100000(?P<barcode>046[0-9]{6})(215.{12}\s*(17\d{6}|7003\d{10})|215.{5}|215.{7})(\s*93.{3}|\s*93.{4}|\s*93.{5})(\s*3103(?P<weight>\d{6}))?",
        "milkBelorus": r"\s*01(?P<barcode>04[0-9]{12})(21.{13}\s*(17\d{6}|7003\d{10})|21.{8})(\s*93.{3}|\s*93.{4}|\s*93.{5})(\s*3103(?P<weight>\d{6}))?",
        "milkNoName": r"\s*01(?P<barcode>086[0-9]{11})(21.{13}\s*(17\d{6}|7003\d{10})|21.{6}|21.{8})(\s*93.{3}|\s*93.{4}|\s*93.{5})(\s*3103(?P<weight>\d{6}))?",
        "milkOld": r"01(?P<barcode>[0-9]{14})21.{6}\s*93.{4}\s*",
        "water": r"01(?P<barcode>[0-9]{14})21.{13}\s*93.{4}\s*",
        "beer": r"01(?P<barcode>[0-9]{14})21.{7}\s*93.{4}\s*",
        "draftbeer": r"01(?P<barcode>[0-9]{14})21.{7}(\x1d|\s*)93.{4}(335[0-6]{1}[0-9]{6}){0,1}\s*",
        "tobacco": r"\d{14}.{15}|01(?P<barcode>\d{14})21.{7}8005\d{6}93.{4}.*",
        "bio": r"01(?P<barcode>[0-9]{14})21.{13}\s*91.{4}\s*92.{44}",
    }
    for key, value in patterns.items():
        if re.search(value, cis):
            return [key, cis]


async def read_barcodes_from_image(image_path) -> list[str]:
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    barcodes = pyzbar.decode(image)
    barcode_data_list = []
    for barcode in barcodes:
        barcode_data = barcode.data.decode("utf-8")
        barcode_data_list.append(barcode_data)
    return barcode_data_list


async def read_datamatrix_from_image(image_path) -> list[str]:
    image = cv2.imread(str(image_path))
    barcodes = decode(image)
    barcode_data_list = [barcode.data.decode("utf-8") for barcode in barcodes]
    return barcode_data_list


class Scanner:
    def __init__(self, dir_path: Path):
        self.path = dir_path
        self.path.mkdir(parents=True, exist_ok=True)

    async def get_barcodes_from_message(
        self, message: Message, log_e: LoggerEGAIS
    ) -> list[str]:
        result = []
        if message.web_app_data is not None:
            datamatrix = message.web_app_data.data.lstrip("\u001d")
            result.append(datamatrix)
            log_e.info(f'Отсканировал сканером "{datamatrix}"')
        elif message.text is not None:
            result.append(message.text)
            log_e.info(f'Написали штрихкод(-а) "{message.text}"')
        elif message.photo is not None or message.document is not None:
            if message.document is not None:
                file_id = message.document.file_id
            elif message.photo is not None:
                file_id = message.photo[-1].file_id
            img = await message.bot.get_file(file_id)
            file = self.path / f"barcode_{message.message_id}.jpg"
            await message.bot.download_file(img.file_path, file)
            log_e.info("Начал сканирование фото на маркировку")
            barcodes = await read_datamatrix_from_image(file)
            if len(barcodes) == 0:
                log_e.info("Начал сканирование фото на штрихкода")
                barcodes = await read_barcodes_from_image(file)
            for barcode in barcodes:
                result.append(barcode)
        return result

    async def get_type_barcode(self, barcodes: list[str | int]) -> list[BarcodeInfo]:
        result = []
        for bcode in barcodes:
            if bcode.isdigit() and (13 >= len(bcode) >= 5):
                result.append(BarcodeInfo(value=bcode, type=BarcodeType.BARCODE))
            elif await regex_check_datamatrix(bcode) is not None:
                result.append(BarcodeInfo(value=bcode, type=BarcodeType.DATAMATRIX))
            else:
                result.append(BarcodeInfo(value=bcode, type=BarcodeType.UNKNOWN))
        return result


if __name__ == "__main__":
    print(regex_check_datamatrix("0104607064461899215FKnrhg93KBjL"))
