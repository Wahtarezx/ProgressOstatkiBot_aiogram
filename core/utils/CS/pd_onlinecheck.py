import enum
from typing import List, Type
from pydantic import BaseModel, Field, computed_field, model_validator
from datetime import datetime

from core.database.artix.model import Valut
from core.database.query_BOT import count_onlinechecks
from core.services.egais.goods.pd_models import Dcode, TmcType


class TmcTypeOnlineCheck(enum.Enum):
    shoes = "shoes"
    protectivemeans = "protectivemeans"
    markedgoods = "markedgoods"
    tobacco = "tobacco"
    alcohol = "alcohol"


class Supplier(BaseModel):
    agentpaymentobject: int
    inn: str
    name: str
    phone: str
    suppliercode: str


class AdditionalPrice(BaseModel):
    barcode: str
    code: int
    documentId: str
    effectiveDate: datetime
    name: str
    packingPrice: int
    price: int


class OcPosition(BaseModel):
    posnum: int = Field(1)
    code: str
    barcode: str
    name: str
    minprice: int = Field(0)
    price: float
    quant: float = Field(1)
    measure: int = Field(1)
    measurename: str = Field("шт")
    isfractionalmeasure: bool = Field(False)
    vatcode: str = Field("301")
    vatrate: int = Field(0)
    vatsum: float = Field(0)
    dept: Dcode = Field(Dcode.alcohol)
    paymentmethod: int = Field(0)
    paymentobject: int = Field(0)
    taramode: int = Field(0)
    tmctype: str | None = Field(None)
    excisemark: str | None = Field(None)
    catalogcode: int = Field(0)

    # supplier: Supplier
    # additionalprices: Optional[Dict[str, AdditionalPrice]]


class Discount(BaseModel):
    campaigncode: int
    campaignname: str
    discountcode: int
    discountmode: int
    discountname: str
    discountrate: float
    discountsum: float
    discounttype: int
    ispositiondiscount: int
    minpriceignored: bool
    posnum: int


class Organization(BaseModel):
    name: str
    inn: str


class Client(BaseModel):
    name: str
    inn: str
    organization: Organization


class Payments(BaseModel):
    type: int = Field(0)
    amount: float = Field(0)
    valcode: int = Field(0)
    valname: str = Field("")


class Document(BaseModel):
    positions: List[OcPosition]
    # discounts: Optional[List[Discount]] = []
    identifier: str = ""
    dontChange: int = Field(0)
    payments: list[Payments] | None = Field(None, title="Оплаты")

    # client: Client

    @computed_field
    def sum(self) -> float:
        return round(sum([pos.price * pos.quant for pos in self.positions]), 2)

    @model_validator(mode="after")
    def correct_amount_payments(self):
        if self.payments is not None:
            self.payments[0].amount = self.sum
        for i, p in enumerate(self.positions, start=1):
            p.posnum = i
        return self

    async def prepare_text(self) -> list[str]:
        result = []
        text = "➖➖➖ℹ️Информацияℹ️➖➖➖\n"
        for i, p in enumerate(self.positions, start=1):
            text += f"Товар #️⃣{i}:\n"
            text += f"➖<b>Наименование</b>: <code>{p.name}</code>\n"
            text += f"➖<b>Цена</b>: <code>{p.price}</code>\n"
            if len(text) > 3000:
                result.append(text)
                text = "➖➖➖ℹ️Продолжение чекаℹ️➖➖➖\n"
        result.append(text)
        return result


class DegustationGood(BaseModel):
    bcode: str = ""
    name: str = ""
    amark: str = ""
    price: float = 0
    quantity: float = 1.00
    dcode: Dcode = Dcode.alcohol


class Degustation(BaseModel):
    goods: list[DegustationGood] = []
    email: str = ""

    def prepare_text(self) -> list[str]:
        result = []
        text = "➖➖➖ℹ️Информацияℹ️➖➖➖\n"
        for i, g in enumerate(self.goods, start=1):
            text += f"Товар #️⃣{i}:\n"
            text += f"➖<b>Наименование</b>: <code>{g.name}</code>\n"
            text += f"➖<b>Штрихкод</b>: <code>{g.bcode}</code>\n"
            text += f"➖<b>Акц.Марка</b>: <code>{g.amark}</code>\n"
            text += f"➖<b>Цена</b>: <code>{g.price}</code>\n"
            if len(text) > 3000:
                result.append(text)
                text = "-"
        result.append(text)
        return result

    def onlinecheck_document(self, valut: Type[Valut]) -> Document:
        positions = []
        c = 0
        for g in self.goods:
            c += 1
            positions.append(
                OcPosition(
                    posnum=c,
                    code=g.bcode,
                    barcode=g.bcode,
                    name=g.name,
                    price=g.price,
                    excisemark=g.amark,
                    tmctype=TmcType.alcohol.name,
                )
            )

        return Document(
            positions=positions,
            payments=[
                Payments(
                    type=valut.type,
                    amount=round(sum([g.price * g.quantity for g in self.goods]), 2),
                    valcode=valut.code,
                    valname=valut.name,
                )
            ],
        )


class OnlineCheck(BaseModel):
    shopcode: int
    cashcode: int
    document: str
    documentid: str = ""
    state: str = Field("NOT_PAID")

    @model_validator(mode="after")
    def documentid(self):
        self.documentid = f"{self.shopcode}{self.cashcode}{str(count_onlinechecks(self.shopcode, self.cashcode) + 1)}"
        return self


if __name__ == "__main__":
    print(
        OnlineCheck(
            shopcode=1306,
            cashcode=1,
            document="test",
        ).model_dump_json()
    )
