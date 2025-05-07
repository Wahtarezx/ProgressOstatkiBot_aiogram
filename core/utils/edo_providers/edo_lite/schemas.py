from typing import List, Optional
from pydantic import BaseModel, Field, computed_field


class Document(BaseModel):
    id: Optional[str] = Field(
        None, description="Идентификатор документа в системе ЭДО Оператора"
    )
    created_at: Optional[int] = Field(
        None, description="Дата создания документа (timestamp)"
    )
    date: Optional[int] = Field(None, description="Дата документа (timestamp)")
    number: Optional[str] = Field(
        None, description="Номер документа (по спецификации integer)"
    )
    processed_at: Optional[int] = Field(
        None, description="Дата последней обработки документа (timestamp)"
    )
    status: Optional[int] = Field(None, description="Числовой статус документа")
    total_price: Optional[int] = Field(
        None, description="Цена с НДС (по спецификации string)"
    )
    total_vat_amount: Optional[int] = Field(
        None, description="Сумма НДС (по спецификации string)"
    )
    type: Optional[int] = Field(
        None, description="Код типа документа (по спецификации integer)"
    )


class Sender(BaseModel):
    id: Optional[int] = Field(
        None, description="Идентификатор получателя в системе ЭДО Оператора"
    )
    inn: Optional[str] = Field(None, description="ИНН получателя")
    kpp: Optional[str] = Field(None, description="КПП получателя")
    ogrn: Optional[str] = Field(None, description="ОГРН получателя")
    name: Optional[str] = Field(None, description="Наименование получателя")
    email: Optional[str] = Field(None, description="E-mail получателя")


class DocumentItem(BaseModel):
    id: Optional[str] = Field(
        None, description="Идентификатор последнего документа цепочки"
    )
    created_at: Optional[int] = Field(
        None, description="Дата создания последнего документа цепочки (timestamp)"
    )
    date: Optional[int] = Field(
        None, description="Дата последнего документа цепочки (timestamp)"
    )
    documents: List[Document] = Field(
        None, description="Список документов в системе ЭДО Оператора"
    )
    group_id: Optional[str] = Field(
        None, description="Идентификатор группы цепочки документов"
    )
    number: Optional[str] = Field(
        None, description="Номер последнего документа в цепочке"
    )
    sender: Sender = Field(None, description="Информация о покупателе")
    status: Optional[int] = Field(
        None, description="Числовой статус последнего документа цепочки"
    )
    total_price: Optional[int] = Field(
        None, description="Общая сумма c НДС (по спецификации string)"
    )
    total_vat_amount: Optional[int] = Field(
        None, description="Общая сумма НДС (по спецификации string)"
    )
    type: Optional[int] = Field(
        None,
        description="Код типа последнего документа в цепочке (по спецификации string)",
    )
    create_time_stamp: Optional[int] = Field(
        None, description="Дата создания документа в формате timestamp"
    )
    export_time_stamp: Optional[int] = Field(
        None, description="Дата последней обработки документа (timestamp)"
    )

    @computed_field
    def type_name(self) -> str:
        types = {
            "112": "Квитанция подтверждения даты отправки",
            "113": "Квитанция извещение о получении файла продавцом",
            "114": "Квитанция предложения об аннулировании документа",
            "115": "Квитанция извещение о получении файла покупателем",
            "200": "УКД с функцией ДИС (корректировка накладной)",
            "201": "УКД с функцией ДИС информация покупателя (корректировка накладной)",
            "202": "УКД с функцией КСЧФ (корректировка счет-фактуры)",
            "204": "УКД с функцией КСЧФДИС (корректировка счет-фактуры+накладная)",
            "205": "УКД с функцией КСЧФДИС информация покупателя (корректировка счет-фактуры+накладная)",
            "400": "УКД(и) с функцией ДИС (Накладная)",
            "500": "УПД с функцией ДОП (Накладная)",
            "501": "УПД с функцией ДОП информация покупателя (Накладная)",
            "502": "УПД с функцией СЧФ (Счёт-фактура)",
            "504": "УПД с функцией СЧФДОП (Счёт-фактура+Накладная)",
            "505": "УПД с функцией СЧФДОП информация покупателя (Счёт-фактура+Накладная)",
            "600": "УКД ДИС (Накладная)",
            "602": "УКД КСЧФ (Корректировочный счёт-фактура)",
            "604": "УКД КСФДИС (Корректировочный счёт-фактура+Документ об изменении стоимости)",
            "700": "УКД(и) ДИС (Накладная)",
            "702": "УКД(и) КСЧФ (Корректировочный счёт-фактура)",
            "704": "УКД(и) КСФДИС (Корректировочный счёт-фактура+Документ об изменении стоимости)",
            "800": "УПД(и) с функцией ДОП (Накладная исправленная)",
            "801": "УПД(и) с функцией ДОП информация покупателя (Накладная исправленная)",
            "802": "УПД(и) с функцией СЧФ (Счёт-фактура)",
            "804": "УПД(и) с функцией СЧФДОП (Счёт-фактура исправленный + Накладная)",
            "805": "УПД(и) с функцией СЧФДОП информация покупателя (Счёт-фактура исправленный + Накладная)",
            "-10001": "Акт сверки",
        }
        return types.get(str(self.type), "Неизвестно")


class Documents(BaseModel):
    items: List[DocumentItem] = Field(
        None, description="Список элементов с информацией о последних документах"
    )
    has_next_page: bool = Field(
        None, description="Признак наличия следующей страницы (true/false)"
    )


class EventDocument(BaseModel):
    id: Optional[str]


class Item(BaseModel):
    id: Optional[str]
    type: Optional[int]
    document: EventDocument


class EventItems(BaseModel):
    items: List[Item]
