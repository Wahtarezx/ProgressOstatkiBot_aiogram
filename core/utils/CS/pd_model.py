from datetime import datetime
from typing import Union

from pydantic import BaseModel, Field


class Client(BaseModel):
    idclient: Union[str, int] = Field("", title="Идентификатор клиента")
    name: str = Field("", title="ФИО")
    text: str | None = Field(None, title="Текст")
    sex: int | None = Field(None, title="0 - мужской, 1 - женский")
    birthday: datetime | None = Field(None, title="Дата рождения")
    specialdate1name: str | None = Field(None, title="Название даты 1")
    specialdate2name: str | None = Field(None, title="Название даты 2")
    specialdate3name: str | None = Field(None, title="Название даты 3")
    zipcode: str | None = Field(None, title="Почтовый индекс")
    address: str | None = Field(None, title="Адрес")
    email: str | None = Field(None, title="Электронная почта")
    webpage: str | None = Field(None, title="Сайт")
    phonenumber: str = Field(None, title="Номер телефона")
    inn: str | None = Field(None, title="ИНН")
    document: str | None = Field(None, title="Документ")
    okpo: str | None = Field(None, title="ОКПО")
    okpd: str | None = Field(None, title="ОКПД")
    occupation: str | None = Field(None, title="Профессия")
    extendedoptions: str | None = Field(None, title="Расширенные параметры")
    codeword: str | None = Field(None, title="Кодовое слово")
    organizationcode: str | None = Field(None, title="Код организации")
    subscriptionadj: int | None = Field(
        None, title="Поиск по согласию на рассылку	0 - нет, 1 - да"
    )


class CardBalance(BaseModel):
    number: str | int = Field("", title="Номер карты")
    accountNumber: str | int = Field("", title="Номер счета")
    status: str = Field("", title="Статус карты")
    balance: int = Field(0, title="Баланс")
    balanceInactive: int = Field(0)


class CardInfo(BaseModel):
    idcard: int | str = Field("", title="Идентификатор карты")
    idcardgroup: int = Field(2, title="Идентификатор группы карт")
    idclient: int | str = Field("", title="Идентификатор клиента")
    number: int | str = Field("", title="Номер карты")
    blocked: int = Field(0, title="Заблокирована")


if __name__ == "__main__":
    c = Client(idclient="123", name="Иванов Иван Иванович")
    print()
