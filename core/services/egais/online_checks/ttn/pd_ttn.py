from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, computed_field, model_validator

from core.services.egais.goods.pd_models import Dcode


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
        return self.short_name if self.short_name else self.full_name


class TtnInfo(BaseModel):
    number: str = Field(..., description="Номер", alias="wb:NUMBER")
    date: datetime = Field(..., description="Дата", alias="wb:Date")
    shipping_date: datetime = Field(
        ..., description="Дата отгрузки", alias="wb:ShippingDate"
    )


class Box(BaseModel):
    number: str = Field(..., description="Номер")
    amcs: list[str] = Field([], description="Акцизные марки")


class Producer(BaseModel):
    ul: UL = Field(..., description="Поставщик", alias="oref:UL")


class Product(BaseModel):
    full_name: str = Field(
        "", description="Полное наименование", alias="pref:FullName", exclude=True
    )
    short_name: str = Field(
        "", description="Полное наименование", alias="pref:ShortName", exclude=True
    )
    alcocode: str = Field("", description="Код АЛКО", alias="pref:AlcCode")
    capacity: float = Field(..., description="Объем", alias="pref:Capacity")
    volume: float = Field(..., description="Объем", alias="pref:AlcVolume")
    vcode: int = Field(..., description="Код вида продукции", alias="pref:ProductVCode")
    producer: Producer = Field(..., description="Производитель", alias="pref:Producer")

    @computed_field
    def name(self) -> str:
        return self.short_name if self.short_name else self.full_name


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


class OnlineCheckTTNOptions(BaseModel):
    overprice_ttn: float = Field(0, description="Процент повышения цены ТТН")
    wb_path: Path | str = Field("", description="Путь к файлу")
    dcode: Dcode = Field(Dcode.alcohol, description="Отдел для товаров")
