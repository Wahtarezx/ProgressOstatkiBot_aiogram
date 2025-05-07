import enum

from pydantic import BaseModel, Field, model_validator


class BarcodeType(enum.Enum):
    BARCODE = "BARCODE"
    DATAMATRIX = "DATAMATRIX"
    UNKNOWN = "UNKNOWN"


class BarcodeInfo(BaseModel):
    type: BarcodeType
    value: str
