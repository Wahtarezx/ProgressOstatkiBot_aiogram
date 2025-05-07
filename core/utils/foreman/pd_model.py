from pathlib import Path
from typing import Union, List, Optional

from pydantic import BaseModel, Field, field_validator, computed_field, model_validator

import config

atol5_taxes = {
    "0": "НДС 0%",
    "1": "НДС 10%",
    "2": "НДС 20%",
    "3": "НДС 10/110",
    "4": "НДС 20/120",
    "5": "БЕЗ НДС",
    "6": "НДС 5%",
    "7": "НДС 7%",
    "8": "НДС 5/105",
    "9": "НДС 7/107",
}

pirit_taxes = {
    "0": "НДС 20%",
    "1": "НДС 10%",
    "2": "НДС 0%",
    "3": "БЕЗ НДС",
    "4": "НДС 20/120",
    "5": "НДС 10/110",
}
shtrih_taxes = {
    "0": "НДС 20%",
    "1": "НДС 10%",
    "2": "НДС 0%",
    "3": "БЕЗ НДС",
    "4": "НДС 20/120",
    "5": "НДС 10/110",
}


class ForemanCash(BaseModel):
    shopcode: int = Field(0, alias="artix_shopcode")
    cashcode: int = Field(0, alias="artix_cashcode")
    artix_shopname: Union[None, str] = Field("", alias="artix_shopname")
    inn: Union[None, str] = Field("", alias="artix_inn")
    kpp: Union[None, str] = Field("", alias="artix_kpp")
    fsrar: Union[None, str] = Field("", alias="artix_fsrar_id_1")
    xapikey: Union[None, str] = Field("", alias="xapikey")
    address: Union[None, str] = Field("", alias="artix_address")
    artix_shopname2: Union[None, str] = Field("", alias="artix_shopname2")
    inn2: Union[None, str] = Field("", alias="artix_inn2")
    kpp2: Union[None, str] = Field("", alias="artix_kpp2")
    fsrar2: Union[None, str] = Field("", alias="artix_fsrar_id_2")
    address2: Union[None, str] = Field("", alias="artix_address2")
    artix_version: Union[None, str] = Field("", alias="artix_version")
    artix_mols: Union[None, str] = Field("", alias="artix_mols")
    tun0: Union[None, str] = Field("", alias="ipaddress_tun0")
    tun1: Union[None, str] = Field("", alias="ipaddress_tun1")
    os_name: Union[None, str] = Field("", alias="lsbdistcodename")
    gui_interface: Union[None, str] = Field("keyboard", alias="artix_gui_interface")
    kkm1_name: Union[None, str] = Field("", alias="artix_kkm_1_producer_name")
    kkm1_producer: Union[None, str] = Field("", alias="artix_kkm_1_producer")
    kkm1_number: Union[None, str] = Field("", alias="artix_kkm_1_number")
    kkm1_firmware: Union[None, str] = Field("", alias="artix_kkm_1_firmware")
    kkm1_departs: Union[None, str] = Field("", alias="artix_kkm1_departmapping")
    kkm1_ffd_version: Union[None, str] = Field("", alias="artix_kkm_1_ffd_version")
    kkm1_fn_number: Union[None, str] = Field("", alias="artix_kkm_1_fn_number")
    kkm1_fn_date_end: Union[None, str] = Field("", alias="artix_kkm_1_fn_time_end")
    kkm1_taxmapping_code: Union[None, str] = Field("", alias="artix_kkm1_taxmapping")
    kkm2_name: Union[None, str] = Field("", alias="artix_kkm_2_producer_name")
    kkm2_producer: Union[None, str] = Field("", alias="artix_kkm_2_producer")
    kkm2_number: Union[None, str] = Field("", alias="artix_kkm_2_number")
    kkm2_firmware: Union[None, str] = Field("", alias="artix_kkm_2_firmware")
    kkm2_departs: Union[None, str] = Field("", alias="artix_kkm2_departmapping")
    kkm2_fn_number: Union[None, str] = Field("", alias="artix_kkm_2_fn_number")
    kkm2_ffd_version: Union[None, str] = Field("", alias="artix_kkm_2_ffd_version")
    kkm2_fn_date_end: Union[None, str] = Field("", alias="artix_kkm_2_fn_time_end")
    kkm2_taxmapping_code: Union[None, str] = Field("", alias="artix_kkm2_taxmapping")
    gost1_date_end: Union[None, str] = Field("", alias="artix_gost_1")
    pki1_date_end: Union[None, str] = Field("", alias="artix_pki_1")
    gost2_date_end: Union[None, str] = Field("", alias="artix_gost_2")
    pki2_date_end: Union[None, str] = Field("", alias="artix_pki_2")
    is_bar: bool = Field(False, alias="is_bar")
    artix_cs_shopid: str = Field("", alias="artix_cs_shopid")

    @field_validator("artix_shopname")
    def check_name1(cls, v):
        if v == "NAME":
            return ""
        return v

    @field_validator("artix_shopname2")
    def check_name2(cls, v):
        if v == "NAME":
            return ""
        return v

    @field_validator("kkm1_name")
    def fr_name(cls, v):
        if v == "Кристалл":
            return "Вики Принт"
        return v

    @field_validator("kkm2_name")
    def fr_name2(cls, v):
        if v == "Кристалл":
            return "Вики Принт"
        return v

    @computed_field
    def list_mols(self) -> List[str]:
        if self.artix_mols is not None:
            return [m for m in self.artix_mols.split(",") if m]
        return []

    @computed_field
    def kkm1_taxmapping(self) -> Union[None, str]:
        if self.kkm1_producer == "1":
            return shtrih_taxes.get(self.kkm1_taxmapping_code, "Неизвестно")
        elif self.kkm1_producer == "4":
            if self.kkm1_firmware.startswith("3."):
                return atol5_taxes.get(self.kkm1_taxmapping_code, "Неизвестно")
            else:
                return atol5_taxes.get(self.kkm1_taxmapping_code, "Неизвестно")
        elif self.kkm1_producer == "5":
            return pirit_taxes.get(self.kkm1_taxmapping_code, "Неизвестно")

    @computed_field
    def kkm2_taxmapping(self) -> Union[None, str]:
        if self.kkm2_producer == "1":
            return shtrih_taxes.get(self.kkm2_taxmapping_code, "Неизвестно")
        elif self.kkm2_producer == "4":
            if self.kkm2_firmware.startswith("3."):
                return atol5_taxes.get(self.kkm2_taxmapping_code, "Неизвестно")
            else:
                return atol5_taxes.get(self.kkm2_taxmapping_code, "Неизвестно")
        elif self.kkm2_producer == "5":
            return pirit_taxes.get(self.kkm2_taxmapping_code, "Неизвестно")

    @model_validator(mode="before")
    def check_shopcode_and_cashcode(before_data: dict):
        if (before_data.get('artix_shopcode') is None) or (before_data.get('artix_cashcode') is None):
            raise ValueError("Вам нужно пройти авторизацию, нажмите кнопку /comp в меню бота")
        return before_data

    def ip(self) -> str:
        if (not self.tun0.startswith("10.8")) and (not self.tun1.startswith("10.8")):
            raise ValueError('Отсутствует IP адрес у кассы. Нажмите кнопку /clear в меню бота, и попробуйте заново.')
        return self.tun0 if self.tun0.startswith("10.8") else self.tun1

    def onlinechecks_file_path(self, file_name: str) -> Path:
        dir = Path(config.server_path, "onlinechecks", str(self.shopcode))
        dir.mkdir(parents=True, exist_ok=True)
        return dir / file_name

    def ref_payload(self, ref_id: str):
        return "/".join(
            [
                str(self.shopcode),
                str(self.cashcode),
                ref_id,
            ]
        )

    def get_IP_inn(self) -> Union[None, str]:
        if self.inn2 is not None:
            if len(self.inn2) == 12:
                return self.inn2
        if self.inn is not None:
            if len(self.inn) == 12:
                return self.inn
    def get_kpp_by_inn(self, inn: str)-> Optional[str]:
        if self.inn2 == inn:
            return self.kpp2
        elif self.inn == inn:
            return self.kpp



class Deeplink(BaseModel):
    shopcode: int
    cashcode: int
    ref_id: str


# Функция для вывода alias каждого поля
def print_field_aliases(model: BaseModel) -> dict:
    return {
        field_name: field_info.alias
        for field_name, field_info in model.__fields__.items()
    }


if __name__ == "__main__":
    print_field_aliases(ForemanCash)
