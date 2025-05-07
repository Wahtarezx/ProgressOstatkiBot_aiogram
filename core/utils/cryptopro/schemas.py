from typing import Optional

from pydantic import BaseModel
from datetime import datetime


class PrivateKey(BaseModel):
    providerName: str
    uniqueContainerName: str
    containerName: str


class Algorithm(BaseModel):
    name: str
    val: str


class Valid(BaseModel):
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class Subject(BaseModel):
    SN: Optional[str] = None
    G: Optional[str] = None
    CN: Optional[str] = None
    C: Optional[str] = None
    SNILS: Optional[str] = None
    OGRNIP: Optional[str] = None
    INN: Optional[str] = None
    E: Optional[str] = None
    UnstructuredName: Optional[str] = None
    row: Optional[str] = None


class CertInfo(BaseModel):
    privateKey: PrivateKey
    algorithm: Algorithm
    valid: Valid
    subject: Subject
    thumbprint: str
    serialNumber: str
    hasPrivateKey: bool
