from datetime import date
from pathlib import Path
from typing import Type

from aiogram import html as h
from pydantic import BaseModel, Field, computed_field, model_validator

from core.database.artix.model import Valut
from core.services.egais.goods.pd_models import Dcode
from core.utils import texts
from core.utils.CS.pd_onlinecheck import Document, Payments, OcPosition


class UL(BaseModel):
    inn: str = Field("", description="ИНН", alias="oref:INN")
    kpp: str = Field("", description="КПП", alias="oref:KPP")
    fsrar: str = Field("", description="ФСРАР", alias="oref:ClientRegId")
    full_name: str = Field(
        "", description="Полное наименование", alias="oref:FullName", exclude=True
    )
    short_name: str = Field(
        "", description="Полное наименование", alias="oref:ShortName", exclude=True
    )

    @computed_field
    def name(self) -> str:
        base_name = self.short_name if self.short_name else self.full_name
        return f"{base_name}"


class TtnInfo(BaseModel):
    number: str = Field(..., description="Номер", alias="wb:NUMBER")
    ttn_date: date = Field(..., description="Дата", alias="wb:Date")
    shipping_date: date = Field(
        ..., description="Дата отгрузки", alias="wb:ShippingDate"
    )


class Box(BaseModel):
    number: str | None = Field(None, description="Номер")
    amcs: list[str] = Field([], description="Акцизные марки")


class Producer(BaseModel):
    ul: UL | None = Field(None, description="Поставщик", alias="oref:UL")


class Product(BaseModel):
    full_name: str = Field(
        "", description="Полное наименование", alias="pref:FullName", exclude=True
    )
    short_name: str = Field(
        "", description="Полное наименование", alias="pref:ShortName", exclude=True
    )
    alcocode: str = Field("", description="Код АЛКО", alias="pref:AlcCode")
    capacity: float = Field(..., description="Объем", alias="pref:Capacity")
    volume: float = Field(..., description="Градусы", alias="pref:AlcVolume")
    vcode: int = Field(..., description="Код вида продукции", alias="pref:ProductVCode")
    producer: Producer | None = Field(
        None, description="Производитель", alias="pref:Producer"
    )

    @computed_field
    def name(self) -> str:
        base_name = self.short_name if self.short_name else self.full_name
        return f"{base_name} {self.capacity:.3f}л {self.volume}%"


class Position(BaseModel):
    id: str = Field("", description="Номер позиции")
    product: Product = Field("", description="Продукция")
    quantity: int = Field("", description="Количество")
    price: float = Field("", description="Закупочная цена")
    ean: str = Field("", description="EAN")
    boxs: list[Box] = Field([], description="Коробки")


class WB4(BaseModel):
    fsrar: str = Field(..., description="ФСРАР")
    ttn_info: TtnInfo = Field(..., description="Информация о ТТН")
    shipper: UL = Field(..., description="Поставщик")
    consignee: UL = Field(..., description="Получатель")
    contents: list[Position] = Field(..., description="Содержание")
    file_path: Path | str = Field("", description="Путь к файлу")

    @computed_field
    def sum(self) -> float:
        s = 0
        for content in self.contents:
            s += content.price * content.quantity
        return round(s, 2)

    def bot_text(self, media: bool = False) -> list[str]:
        result = []
        text = texts.information_head
        text += f"<b>Номер ТТН:</b> <code>{self.ttn_info.number}</code>\n"
        text += f"<b>Дата ТТН:</b> <code>{self.ttn_info.ttn_date}</code>\n"
        text += f"<b>Отгрузка:</b> <code>{self.ttn_info.shipping_date}</code>\n"
        text += f"<b>Поставщик:</b> <code>{self.shipper.name}</code>\n"
        text += f"<b>Сумма:</b> <code>{self.sum}</code>\n"
        text += texts.information_head
        text += f"Название | Кол-во | Цена\n"
        for i, content in enumerate(self.contents, start=1):
            text += f"<u><b>{i})</b></u> {content.product.name} | {content.quantity} шт | {content.price} ₽\n"
            if media:
                if (len(result) == 0 and len(text) > 900) or (
                    len(result) > 0 and len(text) > 3800
                ):
                    result.append(text)
                    text = ""
            else:
                if len(result) > 0 and len(text) > 3800:
                    result.append(text)
                    text = ""

        result.append(text)
        return result

    def onlinecheck_document(
        self, valut: Type[Valut], dcode: Dcode = Dcode.alcohol
    ) -> Document:
        positions = []
        c = 0
        for content in self.contents:
            for box in content.boxs:
                for amc in box.amcs:
                    c += 1
                    positions.append(
                        OcPosition(
                            posnum=c,
                            code=content.ean,
                            barcode=content.ean,
                            name=content.product.name,
                            price=content.price,
                            excisemark=amc,
                            dept=dcode,
                        )
                    )

        return Document(
            positions=positions,
            payments=[
                Payments(
                    type=valut.type,
                    amount=self.sum,
                    valcode=valut.code,
                    valname=valut.name,
                )
            ],
        )

    async def overprice(self, procent: float) -> None:
        if procent == 0:
            return
        for content in self.contents:
            content.price = round(content.price * (1 + procent / 100), 2)
