from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel

from core.utils.redis import RedisConnection


class BaseSeller(BaseModel):
    inn: Optional[str]
    kpp: Optional[str]
    name: Optional[str]


class BaseDocument(BaseModel):
    doc_id: Optional[str]
    doc_name: Optional[str]
    doc_type_name: Optional[str]
    date: Optional[datetime]
    seller: Optional[BaseSeller]
    total_price: Optional[int | float]
    doc_is_acccepted: bool = False


class BaseDocumentWithPDF(BaseDocument):
    pdf: Optional[bytes] = None


class EdoProvider(ABC):
    def __init__(self, inn_to_auth: str, token: str = None, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return str(self.__dict__)

    @abstractmethod
    async def create_token(self):
        pass

    @abstractmethod
    async def accept_document(self, doc_id: str) -> None:
        pass

    @abstractmethod
    async def get_documents_for_accept(self) -> List[BaseDocument]:
        pass

    @abstractmethod
    async def get_documents(self, params: Dict[str, Any] = None) -> List[BaseDocument]:
        pass

    @abstractmethod
    async def get_doc_info_with_pdf(self, doc_id: str) -> BaseDocumentWithPDF:
        pass

    @abstractmethod
    async def save_to_redis(self, rds: RedisConnection) -> dict:
        pass

    @classmethod
    async def load_from_redis(cls, rds: RedisConnection):
        pass
