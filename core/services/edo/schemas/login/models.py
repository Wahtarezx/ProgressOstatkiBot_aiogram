import sys
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, model_validator, field_validator, Field

sys.path.append("/home/zabbix/ProgressOstatkiBot_aiogram")
from core.loggers.make_loggers import znak_log


class EnumEdoProvider(IntEnum):
    """Список доступных провайдеров ЭДО"""

    edolite = 16
    # platforma_edo = 2


class Token(BaseModel):
    token: Optional[str] = None
    end_date: Optional[datetime] = None
    edo_provider: EnumEdoProvider
    # is_main_operator: bool = False
    inn: Optional[str] = None
    thumbprint: Optional[str] = None

    # @model_validator(mode='after')
    # async def recreate_token(self):
    #     # Возвращаем если время токена не вышло
    #     if self.end_date is not None:
    #         if datetime.now() < self.end_date:
    #             return self
    #
    #     znak = Znak(inn_to_auth=self.inn, thumbprint=config.main_thumbprint)
    #     await znak.create_token(self.inn)
    #
    #     if self.edo_provider == EdoProviders.chestnyi_znak:
    #         if znak is not None:
    #             self.token = znak.token
    #             self.end_date = datetime.now() + timedelta(hours=9, minutes=30)
    #     elif self.edo_provider == EdoProviders.platforma_edo:
    #         self.token = OFD(thumbprint=self.thumbprint).token
    #         self.end_date = datetime.now() + timedelta(minutes=30)
    #     return self


class Certificate(BaseModel):
    thumbprint: Optional[str] = None
    cert_from: datetime | None = None
    cert_to: datetime | None = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    middleName: Optional[str] = None
    is_proxy: bool = True
    edo_provider: EnumEdoProvider = EnumEdoProvider.edolite
    inn: str
    kpp: Optional[str] = Field(None, title="КПП или его аналог")
    tokens: list[Token] = Field(default_factory=list)

    @field_validator("inn")
    def check_inn(cls, inn: str):
        if not inn.isdigit():
            raise ValueError(
                "ИНН должен состоять только из цифр\n"
                "Напишите еще раз ответным сообщением ваш <b>ИНН</b>"
            )
        elif len(inn) != 12 and len(inn) != 10:
            raise ValueError(
                f"ИНН должен состоять из 12 или 10 цифр, а ваш состоит из {len(inn)} цифр\n"
                f"Напишите еще раз ответным сообщением ваш <b>ИНН</b>"
            )
        return inn

    @field_validator("tokens")
    def remove_old_tokens(cls, tokens: list[Token]):
        return [token for token in tokens if datetime.now() < token.end_date]

    @model_validator(mode="after")
    def certificate_info(self):
        znak = ""  # TrueApi(inn_to_auth=self.inn, thumbprint=config.main_thumbprint)

        if not self.tokens:
            self.tokens = [
                Token(
                    edo_provider=EnumEdoProvider.edolite,
                    inn=self.inn,
                    token=znak.token,
                    end_date=datetime.now() + timedelta(hours=9, minutes=30),
                    thumbprint=self.thumbprint,
                )
            ]

        if self.firstName is None or self.lastName is None or self.middleName is None:
            try:
                user_info = znak.get_user_info(self.inn)
                fio = user_info.chief[0].split()
                self.firstName = fio[0]
                self.lastName = fio[1]
                self.middleName = " ".join(fio[2:])
            except ValueError as ex:
                znak_log.exception(ex)
                znak_log.error(str(ex))

        profile = znak.profile_info()
        self.kpp = profile.kpp
        for operator in profile.edo_operators:
            if (
                "эдо лайт" in operator.edo_operator_name.lower()
                and operator.is_main_operator
            ):
                self.edo_provider = EnumEdoProvider.edolite
            elif (
                "платформа эдо" in operator.edo_operator_name.lower()
                and operator.is_main_operator
            ):
                # self.tokens.append(Token(inn=self.inn,
                #                          edo_provider=EdoProviders.platforma_edo,
                #                          thumbprint=self.thumbprint))
                self.edo_provider = EnumEdoProvider.platforma_edo
        return self

    def main_token(self) -> Token:
        for token in self.tokens:
            if token.edo_provider == self.edo_provider:
                return token
        token = Token(
            edo_provider=self.edo_provider, inn=self.inn, thumbprint=self.thumbprint
        )
        self.tokens.append(token)
        return token

    def get_token_chz(self) -> Token:
        for token in self.tokens:
            if token.edo_provider == EnumEdoProvider.edolite:
                return token
        token = Token(
            edo_provider=EnumEdoProvider.edolite,
            inn=self.inn,
            thumbprint=self.thumbprint,
        )

        self.tokens.append(token)
        return token

    def get_fio(self):
        return f"{self.lastName} {self.firstName} {self.middleName}"


class Test(BaseModel):
    inn: str

    @field_validator("inn")
    def test(cls, v: str):
        raise ValueError("123")
