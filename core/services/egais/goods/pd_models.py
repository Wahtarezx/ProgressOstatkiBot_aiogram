import enum
from datetime import datetime
from enum import IntEnum
from typing import Union, List, Optional

from pydantic import BaseModel, Field

from core.database.modelBOT import BarcodesStatus
from core.services.markirovka.pd_models.gismt import GisMtProductInfo


class TmcType(IntEnum):
    basic = 0
    alcohol = 1
    alcohol_set = 2
    tobacco = 3
    shoes = 4
    medicinal = 5
    protectivemeans = 6
    markedgoods = 7
    draftbeer = 8


class Dcode(IntEnum):
    alcohol = 1
    beer = 2
    tobacco = 3
    basic = 4
    markirovka = 5
    dummy = 9


class OpMode(IntEnum):
    basic = 0
    beer = 64
    alcohol = 192
    tobacco = 32768


class Measure(IntEnum):
    unit = 1
    kg = 2
    litr = 779


class UpdateHotkeyType(enum.Enum):
    APPEND = "APPEND"
    UPDATE = "UPDATE"


class DraftBeerInfo(BaseModel):
    participantInn: str = Field(title="ИНН участника оборота товаров", default="")
    participantKpp: str = Field(
        title="КПП торговой точки. Обязательно заполнен для юр.лиц", default=""
    )
    fiasId: str = Field(title="Идентификатор ФИАС. Обязательно для ИП", default="")
    volume_draftbeer: float = Field(title="Объем кеги", default=0)
    expirationDate: datetime = Field(
        title="Предельная дата реализации", default_factory=datetime.now
    )
    connectDate: datetime = Field(
        title="Предельная дата реализации", default_factory=datetime.now
    )
    cis: str = Field(title="Код марки", default="")
    bcode: str = Field(title="Штрихкод", default="")
    name: str = Field(title="Название товара", default="")


class _Actionpanelitem(BaseModel):
    actionpanelitemcode: int
    name: str
    color: str | None
    actionpanelcode: int
    actioncode: int
    row: int
    column: int
    rowspan: int
    columnspan: int


class _Actionparameter(BaseModel):
    actionparametercode: int
    parameterorder: int
    parametervalue: str
    cmactioncode: int
    parametername: str


class _Hotkey(BaseModel):
    hotkeycode: int
    hotkeyname: str
    bybarcode: bool


class _HotkeyInvent(BaseModel):
    hotkeyinventid: int
    inventcode: str
    hotkeycode: int


class TouchPanel(BaseModel):
    actionpanelitem: Union[_Actionpanelitem, None]
    actionpanelparameter: Union[_Actionparameter, None]
    hotkey: Union[_Hotkey, None]
    hotkeyInvents: Union[List[_HotkeyInvent], None]
    type: UpdateHotkeyType


class Product(BaseModel):
    name: str = Field(title="Название товара", default="")
    bcode: str = Field(title="Штрихкод", default="")
    cis: str = Field(title="Маркировка", default="")
    op_mode: int = Field(title="Свойства товара", default=0)
    measure: int = Field(title="Единица измерения", default=1)
    dcode: Dcode = Field(title="Отдел", default=Dcode.basic)
    tmctype: TmcType = Field(title="Тип товара", default=TmcType.basic)
    qdefault: int = Field(title="Количество по умолчанию", default=1)
    draftbeer: DraftBeerInfo = Field(
        title="Информация о разливном пиве",
        default=DraftBeerInfo(volume_draftbeer=0, expirationDate=datetime.now()),
    )
    pdinfo: Union[GisMtProductInfo, None] = Field(
        title="Информация о продукте", default=None
    )
    price: Optional[float] = Field(title="Цена", default=0)
    touch: Union[TouchPanel, None] = Field(
        title="Взаимодействия с Touch-интерфейсом", default=None
    )


class _Goods(BaseModel):
    status: BarcodesStatus = Field(title="Статус товара", default=BarcodesStatus.add)
    products: list[Product] = Field(title="Товары", default=[])

    def prepare_text(self) -> list[str]:
        result = []
        text = "➖➖➖ℹ️Информацияℹ️➖➖➖\n"
        for i, product in enumerate(self.products, start=1):
            text += f"Товар #️⃣{i}:\n"
            text += f"➖<b>Наименование</b>: <code>{product.name}</code>\n"
            text += f"➖<b>Штрихкод</b>: <code>{product.bcode}</code>\n"
            text += f"➖<b>Цена</b>: <code>{product.price}</code>\n"
            if product.dcode == Dcode.alcohol:
                text += f"➖<b>Тип товара</b>: <code>Алкоголь</code>\n"
            elif product.dcode == Dcode.beer:
                if product.tmctype == TmcType.draftbeer:
                    text += f"➖<b>Объем кеги</b>: <code>{product.draftbeer.volume_draftbeer}</code>\n"
                    text += f"➖<b>Тип товара</b>: <code>Разливное пиво</code>\n"
                elif product.tmctype == TmcType.markedgoods:
                    text += f"➖<b>Тип товара</b>: <code>Маркированное пиво</code>\n"
            elif product.dcode == Dcode.tobacco:
                text += f"➖<b>Тип товара</b>: <code>Сигареты</code>\n"
            elif product.dcode == Dcode.basic:
                text += f"➖<b>Тип товара</b>: <code>Продукты</code>\n"
            elif product.dcode == Dcode.markirovka:
                text += f"➖<b>Тип товара</b>: <code>Маркированный товар</code>\n"
            if len(text) > 3000:
                result.append(text)
                text = "-"
        result.append(text)
        return result


class RozlivAlco(BaseModel):
    goods: list[DraftBeerInfo] = Field(title="Товары", default=[])

    def prepare_text(self) -> list[str]:
        result = []
        text = "➖➖➖ℹ️Информацияℹ️➖➖➖\n"
        for i, g in enumerate(self.goods, start=1):
            text += f"Товар #️⃣{i}:\n"
            text += f"➖<b>Название</b>: <code>{g.name}</code>\n"
            text += f"➖<b>Штрихкод</b>: <code>{g.bcode}</code>\n"
            text += f"➖<b>Акц.Марка</b>: <code>{g.cis}</code>\n"
            text += f"➖<b>Объем</b>: <code>{g.volume_draftbeer}</code>\n"
            if len(text) > 3000:
                result.append(text)
                text = "-"
        result.append(text)
        return result
