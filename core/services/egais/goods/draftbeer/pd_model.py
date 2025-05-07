import json
import re
from datetime import datetime
from typing import Union

from pydantic import BaseModel, Field

from core.database.artix.querys import ArtixCashDB
from core.services.markirovka.pd_models.gismt import MOD, GisMtProductInfo
from core.utils import texts
from core.utils.foreman.pd_model import ForemanCash


class Profile(BaseModel):
    fio: str = Field("", title="ФИО")
    inn: str = Field("", title="ИНН")


class Code(BaseModel):
    cis: str = Field(..., title="Код маркировки")
    gtin: str = Field("", title="GTIN")
    expirationDate: Union[datetime, None] = Field(
        default_factory=datetime.now, title="Предельная дата реализации"
    )
    connectDate: datetime = Field(
        default_factory=datetime.now, title="Дата подключения"
    )
    pdinfo: GisMtProductInfo | None = Field(None, title="Информация о продукте")


class DraftBeer(BaseModel):
    codes: list[Code] = Field([], title="Коды маркировок")
    profile: Profile | None = Field(None, title="Профиль")
    mod: MOD | None = Field(None, title="МОД")

    async def prepare_commit_text(self) -> list[str]:
        result = []
        text = texts.information_head
        text += f"<b>МОД</b>: <code>{self.mod.address}</code>\n"
        for i, code in enumerate(self.codes, start=1):
            text += f"Кега #️⃣{i}:\n"
            text += f"➖<b>Наименование</b>: <code>{code.pdinfo.name}</code>\n"
            text += f"➖<b>Штрихкод</b>: <code>{code.pdinfo.gtin}</code>\n"
            text += (
                f"➖<b>Объём</b>: <code>{code.pdinfo.coreVolume / 1000}</code> литров\n"
            )
            # text += f'➖<b>Срок годности</b>: <code>{code.expirationDate}</code>\n'
            if len(text) > 3000:
                result.append(text)
                text = "-"
        result.append(text)
        return result

    async def edo_doc(self) -> str:
        if self.mod.fiasId:
            doc = {
                "participantInn": self.profile.inn,
                "fiasId": self.mod.fiasId,
                "codes": [
                    {
                        "cis": code.cis.split("\x1d")[0],
                        "connectDate": code.connectDate.strftime("%Y-%m-%d"),
                        # "expirationDate": code.expirationDate.strftime('%Y-%m-%d')
                    }
                    for code in self.codes
                ],
            }
        else:
            doc = {
                "participantInn": self.profile.inn,
                "participantKpp": self.mod.kpp,
                "codes": [
                    {
                        "cis": code.cis.split("\x1d")[0],
                        "connectDate": code.connectDate.strftime("%Y-%m-%d"),
                        # "expirationDate": code.expirationDate.strftime('%Y-%m-%d')
                    }
                    for code in self.codes
                ],
            }
        return json.dumps(doc)

    async def commit_to_artix(self, cash: ForemanCash) -> None:
        for code in self.codes:
            artix = ArtixCashDB(cash.ip())
            await artix.insert_draftbeer_ostatki(
                cis=code.cis,
                bcode=re.findall(r"0*([0-9]+)", code.gtin)[0],
                name=code.pdinfo.name,
                expirationdate=code.expirationDate,
                connectdate=code.connectDate,
                volume=code.pdinfo.coreVolume / 1000,
            )
