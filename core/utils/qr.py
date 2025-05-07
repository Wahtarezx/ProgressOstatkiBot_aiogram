from io import BytesIO

import qrcode
from pathlib import Path
from config import dir_path


async def generate_qr(text: str | int) -> Path:
    qr_dir = Path(dir_path, "files", "qr")
    qr_dir.mkdir(parents=True, exist_ok=True)
    qr_path = qr_dir / f"{str(text)}.png"
    if qr_path.exists():
        return qr_path
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(str(text))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(str(qr_path))
    return qr_path


async def get_buffer_qr(text: str | int) -> bytes:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(str(text))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Используем BytesIO для получения байтового представления изображения
    buffer = BytesIO()
    img.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
