from pydantic import BaseModel, Field, field_validator, model_validator


class Waybills(BaseModel):
    inn: str
    fsrar: str
    port: str
