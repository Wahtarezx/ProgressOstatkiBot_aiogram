from datetime import datetime

from pydantic import BaseModel, Field
from typing import Union
from core.database.query_PROGRESS import get_cash_info


class Cash(BaseModel):
    id: int = Field(title="ID строки в БД")
    name: Union[str, None] = Field(title="Номер компьютера", default=None)
    inn: Union[str, None] = Field(title="ИНН порта 8082", default=None)
    kpp: Union[str, None] = Field(title="КПП порта 8082", default=None)
    fsrar: Union[str, None] = Field(title="ФСРАР порта 8082", default=None)
    fsrar2: Union[str, None] = Field(title="ФСРАР порта 18082", default=None)
    address: Union[str, None] = Field(title="Адрес торговой точки", default=None)
    ooo_name: Union[str, None] = Field(
        title="Название юр лица на порту 8082", default=None
    )
    ip_name: Union[str, None] = Field(
        title="Название юр лица на порту 18082", default=None
    )
    ip_inn: Union[str, None] = Field(title="ИНН порта 18082", default=None)
    ip: Union[str, None] = Field(title="IP кассы", default=None)
    touch_panel: bool = Field(title="Касса имеет графический интерфейс?")


class ClientAutologins(BaseModel):
    id: int = Field(title="ID строки в БД")
    date: datetime
    shopcode: int
    cashcode: int
    user_id: str
    inn: str


class Client(BaseModel):
    date: datetime
    phone_number: Union[str, None] = Field(title="Номер телефона", default=None)
    first_name: Union[str, None] = Field(title="Имя", default=None)
    last_name: Union[str, None] = Field(title="Фамилия", default=None)
    user_id: Union[str, None] = Field(title="ID пользователя", default=None)
    chat_id: Union[str, None] = Field(title="ID чата", default=None)
    cash: Union[str, None]
    admin: Union[bool, None] = Field(title="Админ", default=None)
    whitelist_admin: Union[bool, None] = Field(title="Белый список", default=None)
    accept_admin: Union[bool, None] = Field(
        title="Приём без сканирования", default=None
    )
    edo_admin: Union[bool, None] = Field(title="ЭДО", default=None)
    autologins: list[ClientAutologins] = Field([], title="Авторизации")


if __name__ == "__main__":
    cash = get_cash_info("123")
    if cash is not None:
        print(Cash(**cash.__dict__))
