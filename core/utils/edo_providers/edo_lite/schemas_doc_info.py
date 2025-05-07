from typing import List, Optional

from pydantic import BaseModel, computed_field


class Address(BaseModel):
    region: Optional[dict] = None
    postal_code: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    street: Optional[str] = None
    plot: Optional[str] = None
    office: Optional[str] = None


class Bank(BaseModel):
    number_sch: Optional[str] = None
    name: Optional[str] = None
    bic: Optional[str] = None
    corr_sch: Optional[str] = None


class Participant(BaseModel):
    id: Optional[int] = None
    participant_type: Optional[int] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    name: Optional[str] = None
    address: Optional[Address] = None
    okpo: Optional[str] = None
    bank: Optional[Bank] = None
    name_ul: Optional[str] = None
    name_ip: Optional[str] = None
    contact: Optional[dict] = None


class Unit(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None


class GoodIdentificationNumber(BaseModel):
    pack_num: Optional[List[str]] = None


class Product(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    unit: Optional[Unit] = None
    quantity: Optional[str] = None
    price_per_unit: Optional[str] = None
    price: Optional[str] = None
    price_without_vat: Optional[str] = None
    vat_amount: Optional[str] = None
    vat_rate: Optional[str] = None
    details: Optional[List[str]] = None
    good_identification_numbers: Optional[List[GoodIdentificationNumber]] = None
    number: Optional[str] = None
    tov_work: Optional[str] = None


class Currency(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None


class ShipmentEmployee(BaseModel):
    name: Optional[str] = None
    surname: Optional[str] = None
    patronymic: Optional[str] = None
    position: Optional[str] = None


class GroundDocument(BaseModel):
    title: Optional[str] = None
    number: Optional[str] = None
    date: Optional[int] = None


class Shipment(BaseModel):
    content_operation: Optional[str] = None
    employee: Optional[ShipmentEmployee] = None
    grounds_documents: Optional[List[GroundDocument]] = None


class Signer(BaseModel):
    surname: Optional[str] = None
    name: Optional[str] = None
    patronymic: Optional[str] = None
    position: Optional[str] = None
    authority: Optional[int] = None
    grounds: Optional[str] = None
    status: Optional[int] = None


class ShipmentConfirmation(BaseModel):
    doc_name: Optional[str] = None
    doc_number: Optional[str] = None
    doc_date: Optional[int] = None


class DataDocument(BaseModel):
    id_file: Optional[str] = None
    vers_form: Optional[str] = None
    vers_prog: Optional[str] = None
    id_sender: Optional[str] = None
    id_recipient: Optional[str] = None
    name_company_sender: Optional[str] = None
    inn_company_sender: Optional[str] = None
    id_operator_sender: Optional[str] = None
    knd: Optional[str] = None
    function: Optional[str] = None
    date_file: Optional[int] = None
    time_file: Optional[int] = None
    name_company: Optional[str] = None
    name_fact: Optional[str] = None
    name_first_doc: Optional[str] = None


class SignatureSenderCertificate(BaseModel):
    serial_number: Optional[str] = None
    valid_from: Optional[int] = None
    valid_to: Optional[int] = None
    subject: Optional[str] = None
    name: Optional[str] = None
    surname: Optional[str] = None
    inn: Optional[str] = None
    organization: Optional[str] = None


class SignatureSender(BaseModel):
    is_valid: Optional[bool] = None
    created_at: Optional[int] = None
    certificate: Optional[SignatureSenderCertificate] = None


class Sender(BaseModel):
    id: Optional[int] = None
    extra_id: Optional[str] = None
    participant_type: Optional[int] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    ogrn: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None


class CheckGis(BaseModel):
    status: Optional[int] = None
    date: Optional[int] = None


class DocInfo(BaseModel):
    id: Optional[str] = None
    type: Optional[int] = None
    status: Optional[int] = None
    content: Optional[dict] = {}
    sender: Optional[Sender] = None
    number: Optional[str] = None
    product_group: Optional[int] = None
    signature_sender: Optional[SignatureSender]
    is_title_signed: Optional[bool] = None
    created_by: Optional[int] = None
    created_hub: Optional[bool] = None
    actions: Optional[List[str]] = None
    has_mchd: Optional[bool] = None
    send_mchd_file: Optional[bool] = None
    check_gis: Optional[CheckGis] = None

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
