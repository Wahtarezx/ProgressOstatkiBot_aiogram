import asyncio
import math
import os.path

from PIL import Image, ImageDraw, ImageFont
from barcode.codex import Code128
from barcode.writer import ImageWriter
from reportlab.lib import utils
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

import config
from core.database.query_BOT import create_barcode
from core.loggers.make_loggers import bot_log


def generate_pdf(cash_number):
    """
    :param cash_number: Номер компьютера
    :return: путь к файлу PDF
    """
    path = os.path.join(config.dir_path, "files", "barcodes", cash_number)
    images_paths = [
        os.path.join(path, img) for img in os.listdir(path) if img.endswith("png")
    ]
    images_paths = sorted(images_paths, key=os.path.getctime)

    page_width, page_height = letter
    pdf_path = os.path.join(path, f"barcodes.pdf")
    pdf_file = canvas.Canvas(pdf_path, pagesize=letter)

    current_x = 0
    current_y = page_height
    margin = 10

    for idx, image_path in enumerate(images_paths):
        img_width, img_height = utils.ImageReader(image_path).getSize()

        if current_y - img_height < 0:
            pdf_file.showPage()
            current_y = page_height
            current_x = 0

        if page_width - img_width < 0:
            continue  # Пропуск изображений, которые шире страницы

        # Если индекс изображения чётный, размещаем ближе к правому краю
        if idx % 2 == 0:
            current_x = margin
        else:
            current_x = page_width - img_width - margin

        pdf_file.drawImage(
            image_path,
            current_x,
            current_y - img_height,
            width=img_width,
            height=img_height,
        )

        if idx % 2 != 0:
            current_y -= img_height + margin

    pdf_file.save()
    return pdf_path


async def generate_barcode(
    cash_number: str,
    name: str,
    op_mode: int,
    measure: int,
    dcode: int,
    tmctype: int,
    price: str,
    bcode=None,
    qdefault: int = 1,
):
    """
    Создает png со штрихкодом
    :param qdefault: Количество по умолчанию
    :param price: Цена товара
    :param tmctype: Тип товара, указывается в таблице barcodes
    :param bcode: цифры штрихкода
    :param cash_number: Номер компьютера целиком
    :param name: Название товара
    :param op_mode: op_mode Товара
    :param measure: Единица измерения, где 1 - шт, 2 - кг
    :param dcode: Отдел товара
    :return: Путь к рисунку, barcode_number
    """
    dirpath = os.path.join(config.dir_path, "files", "barcodes", str(cash_number))
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)
    if bcode is None:
        cash = cash_number.split("-")[1]
        count_bcodes = len([_ for _ in os.listdir(dirpath) if _.startswith(cash)])
        if config.develope_mode:
            bcode = f"{cash}-"
        else:
            bcode = f"{cash}*"
        bcode = f"{bcode}{count_bcodes + 1}" if len(bcode) <= 7 else bcode
        bot_log.info(f'Сгенерированный ШК: "{bcode}"')
    path = os.path.join(dirpath, f"{bcode}")
    my_code = Code128(bcode, writer=ImageWriter())
    options = {
        "font_size": 2,
        "text_distance": 1.0,
        "font_path": os.path.join(config.dir_path, "files", "Ermilov-bold.otf"),
        "module_height": 4.0,
        "quiet_zone": 1,
        "module_width": 0.15,
    }
    my_code.save(path, options=options)
    path = f"{path}.png"
    im = Image.open(path)
    old_width, old_height = im.size
    # if len(name) * 10 > old_width:
    #     im.close()
    #     os.remove(path)
    #     raise ValueError('Длина изображение выше допустимой нормы')
    # else:
    canvas_width = old_width
    canvas_height = old_height + 30

    x1 = int(math.floor((canvas_width - old_width) / 2))
    y1 = int(math.floor((canvas_height - old_height) / 2))

    mode = im.mode
    new_background = (255, 255, 255)
    if len(mode) == 1:  # L, 1
        new_background = 255
    if len(mode) == 3:  # RGB
        new_background = (255, 255, 255)
    if len(mode) == 4:  # RGBA, CMYK
        new_background = (255, 255, 255, 255)

    newImage = Image.new(mode, (canvas_width, canvas_height - 30), new_background)
    newImage.paste(im, (x1, y1, x1 + old_width, y1 + old_height))
    draw = ImageDraw.Draw(newImage)

    font = ImageFont.truetype(
        os.path.join(config.dir_path, "files", "Ermilov-bold.otf"), 10
    )
    w, h = draw.textsize(name, font=font)
    xy = (((canvas_width - w) / 2), 10)

    draw.text(xy, name, font=font, fill="black", align="center")
    newImage.save(path)
    if not config.develope_mode:
        await create_barcode(
            cash_number=cash_number,
            name=name,
            op_mode=op_mode,
            measure=measure,
            dcode=dcode,
            bcode=bcode,
            tmctype=tmctype,
            qdefault=qdefault,
            price=price,
        )
    return path


if __name__ == "__main__":
    names = [
        'ВОДКА "ТАЙГА" 40% 0,1Л',
        "ВОДКА ТАЙГА 0.25Л РОССИЯ 40%",
        'Водка "Белая Березка" 0.5л. 1/12',
        "Коньяк СТАРЫЙ КУПАЖ 0.25  3*",
        "Напиток Ред Булл 0.473 ж/б",
        "Газ.нап РедБулл энергетический 0.25л ж/б",
        "Мальбро  169р",
        'Сигареты   "MARLBORO" GoId DriginaI"',
        "Пиво Козел",
        'Вино сладкое красное "Соборное" 0.7500л',
        "старый мельник из боченка 0,5",
        "Пломбир кедровый цельные орешки",
    ]
    paths = []
    for i in names:
        try:
            paths.append(
                asyncio.run(
                    generate_barcode(
                        cash_number="cash-887-1",
                        name=i,
                        op_mode=192,
                        measure=1,
                        dcode=1,
                        tmctype=7,
                        price="30",
                    )
                )
            )
        except ValueError:
            print(f"VALUES = {i}")
            continue
    print(generate_pdf("cash-887-1"))
