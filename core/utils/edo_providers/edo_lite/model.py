from datetime import datetime
from pathlib import Path
from typing import List, Any, Dict

from aiogram.client.session import aiohttp
from aiohttp import ClientResponse
from pydantic import TypeAdapter

import config
from config import edolite_cfg
from core.loggers.make_loggers import edolite_log
from core.services.markirovka.trueapi import TrueApi
from core.utils.cryptopro.cryptopro import cryptoPro
from core.utils.edo_providers.base_model import (
    EdoProvider,
    BaseDocument,
    BaseDocumentWithPDF,
    BaseSeller,
)
from core.utils.edo_providers.edo_lite.schemas import Documents, EventItems
from core.utils.edo_providers.edo_lite.schemas_doc_info import DocInfo
from core.utils.redis import RedisConnection


class EdoLiteError(Exception):
    pass


class EdoLite(EdoProvider):
    def __init__(self, inn_to_auth: str, token: str, **kwargs) -> None:
        super().__init__(inn_to_auth, token, **kwargs)
        self.token = token
        self.inn_to_auth = inn_to_auth
        self._end_date_token: float = kwargs.get("_end_date_token")
        self.url = edolite_cfg.URL.rstrip("/")
        self.log_dir = str(Path(config.dir_path, "files", "documents", "edolite"))

    async def __request(
        self,
        method: str,
        url: str,
        params: dict = None,
        headers: dict = None,
        data: dict = None,
        json: dict = None,
        to_return: str = "json",
    ) -> ClientResponse:
        edolite_log.bind(url=url, headers=headers, data=data).info(f"{method} {url}")
        headers = (
            {"Authorization": f"Bearer {self.token}"}
            if headers is None
            else {"Authorization": f"Bearer {self.token}", **headers}
        )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, url, params=params, headers=headers, data=data, json=json
                ) as response:
                    log = edolite_log.bind(
                        status_code=response.status, url=response.url
                    )
                    if response.ok:
                        if to_return == "json":
                            content_response = await response.json()
                        elif to_return == "text":
                            content_response = await response.text()
                        elif to_return == "bytes":
                            content_response = await response.read()
                        log.success(content_response)
                        return content_response
                    else:
                        error_text = await response.text()
                        log.error(error_text)
                        raise EdoLiteError(error_text, response.status)
        except aiohttp.ClientError as e:
            edolite_log.error(f"HTTP request failed: {e}")
            raise

    async def create_token(self) -> None:
        trueapi = TrueApi(inn_to_auth=self.inn_to_auth)
        await trueapi.create_token(self.inn_to_auth)
        self.token = trueapi.token
        self._end_date_token = trueapi.get_end_date_token

    async def get_documents_for_accept(self, args: dict = None):
        """Получение списка входящих документов"""
        url = f"{self.url}/api/v1/incoming-documents"
        docs: Documents = TypeAdapter(Documents).validate_python(
            await self.__request(
                "GET", url, params=[("status", "3"), ("status", "13"), ("limit", "70")]
            )
        )
        base_doc = [
            BaseDocument(
                doc_id=di.id,
                doc_name=di.number,
                doc_type_name=di.type_name,
                doc_is_acccepted=True if di.status in [3, 13] else False,
                total_price=di.total_price,
                date=datetime.fromtimestamp(di.date),
                seller=BaseSeller(
                    inn=di.sender.inn,
                    kpp=di.sender.kpp,
                    name=di.sender.name,
                ),
            )
            for di in docs.items
        ]
        return base_doc

    async def get_documents(self, params: Dict[str, Any] = None) -> List[BaseDocument]:
        url = f"{self.url}/api/v1/incoming-documents"
        docs: Documents = TypeAdapter(Documents).validate_python(
            await self.__request("GET", url, params=params)
        )
        base_doc = [
            BaseDocument(
                doc_id=di.id,
                doc_name=di.number,
                doc_type_name=di.type_name,
                total_price=di.total_price,
                date=datetime.fromtimestamp(di.date),
                seller=BaseSeller(
                    inn=di.sender.inn,
                    kpp=di.sender.kpp,
                    name=di.sender.name,
                ),
            )
            for di in docs.items
        ]
        return base_doc

    async def get_doc_info_with_pdf(self, doc_id: str) -> BaseDocumentWithPDF:
        doc = await self.get_incoming_document(doc_id)
        return BaseDocumentWithPDF(
            doc_id=doc.id,
            doc_name=doc.number,
            doc_type_name=doc.type_name,
            doc_is_acccepted=True if doc.status in [61, 63] else False,
            date=datetime.fromtimestamp(doc.content.get("date", 0)),
            pdf=await self.get_incoming_document_print(doc_id),
            total_price=doc.content.get("total_price", 0),
            seller=BaseSeller(
                inn=doc.sender.inn, kpp=doc.sender.kpp, name=doc.sender.name
            ),
        )

    async def get_outgoing_documents(self, args: dict = None) -> list[Documents]:
        """Получение списка исходящих документов"""
        url = f"{self.url}/api/v1/outgoing-documents"
        return TypeAdapter(Documents).validate_python(
            await self.__request("GET", url, params=args)
        )

    async def get_incoming_document_content(
        self, doc_id: str, args: dict = None
    ) -> bytes:
        """Получение содержимого документа"""
        url = f"{self.url}/api/v1/incoming-documents/{doc_id}/content"
        headers = {"accept": "application/json", "Accept-Encoding": "gzip, deflate, br"}
        return await self.__request(
            "GET", url, params=args, headers=headers, to_return="bytes"
        )

    async def get_outgoing_document_content(
        self, doc_id: str, args: dict = None
    ) -> bytes:
        """Получение содержимого документа"""
        url = f"{self.url}/api/v1/outgoing-documents/{doc_id}/content"
        headers = {"accept": "application/json", "Accept-Encoding": "gzip, deflate, br"}
        return await self.__request(
            "GET", url, params=args, headers=headers, to_return="bytes"
        )

    async def get_incoming_document_event_content(
        self, doc_id: str, event_id: str, args: dict = None
    ) -> bytes:
        """Получение содержимого документа"""
        url = f"{self.url}/api/v1/incoming-documents/{doc_id}/events/{event_id}/content"
        headers = {"accept": "application/json", "Accept-Encoding": "gzip, deflate, br"}
        return await self.__request(
            "GET", url, params=args, headers=headers, to_return="bytes"
        )

    async def get_outgoing_document_event_content(
        self, doc_id: str, event_id: str, args: dict = None
    ) -> bytes:
        """Получение содержимого документа"""
        url = f"{self.url}/api/v1/outgoing_documents/{doc_id}/events/{event_id}/content"
        headers = {"accept": "application/json", "Accept-Encoding": "gzip, deflate, br"}
        return await self.__request(
            "GET", url, params=args, headers=headers, to_return="bytes"
        )

    async def get_incoming_document(self, doc_id: str, args: dict = None) -> DocInfo:
        """Получение информации о документе в JSON"""
        url = f"{self.url}/api/v1/incoming-documents/{doc_id}"
        return TypeAdapter(DocInfo).validate_python(
            await self.__request("GET", url, params=args)
        )

    async def get_outgoing_document(self, doc_id: str, args: dict = None) -> DocInfo:
        """Получение информации о документе в JSON"""
        url = f"{self.url}/api/v1/outgoing-documents/{doc_id}"
        return TypeAdapter(DocInfo).validate_python(
            await self.__request("GET", url, params=args)
        )

    async def get_incoming_documents_unsigned_events(
        self, args: dict = None
    ) -> EventItems:
        """Получение списка входящих квитанций для подписания"""
        url = f"{self.url}/api/v1/incoming-documents/unsigned-events"
        return TypeAdapter(EventItems).validate_python(
            await self.__request("GET", url, params=args)
        )

    async def get_outgoing_documents_unsigned_events(
        self, args: dict = None
    ) -> EventItems:
        """Получение списка исходящих квитанций для подписания"""
        url = f"{self.url}/api/v1/outgoing-documents/unsigned-events"
        return TypeAdapter(EventItems).validate_python(
            await self.__request("GET", url, params=args)
        )

    async def send_incoming_document_event(
        self, doc_id: str, args: dict = None
    ) -> dict:
        """Подписание входящей квитанции"""
        url = f"{self.url}/api/v1/incoming-documents/{doc_id}/events"
        cert_info = await cryptoPro.get_certificate_info()
        familya, name, otchestvo = cert_info.subject.CN.split()

        data = {
            "status": 4,
            "content": {
                "acceptance": {
                    "content_code": {"code": 1},
                    "date": int(datetime.now().timestamp()),
                    "employee": {
                        "position": "Директор",
                        "surname": familya,
                        "name": name,
                        "authority": "Должностные обязанности",
                    },
                },
                "author": {
                    "name": f"{cert_info.subject.CN}, ИНН: {cert_info.subject.INN}"
                },
                "signer": {
                    "name": name,
                    "surname": familya,
                    "patronymic": otchestvo,
                    "inn": cert_info.subject.INN,
                    "details": "",
                    "grounds": "Должностные обязанности",
                    "status": 5,
                    "authority": 1,
                    "way_confirm": "1",
                },
            },
        }
        headers = {"Content-Type": "application/json", "accept": "application/json"}
        return await self.__request(
            "POST",
            url,
            params=args,
            headers=headers,
            json=data,
        )

    async def send_incoming_document_event_signature(
        self, doc_id: str, event_id: str, sign_content: str
    ) -> dict:
        url = (
            f"{self.url}/api/v1/incoming-documents/{doc_id}/events/{event_id}/signature"
        )
        headers = {"Content-Encoding": "base64", "Content-Type": "text/plain"}
        return await self.__request(
            "POST", url, headers=headers, data=sign_content, to_return="text"
        )

    async def send_outgoing_document_event_signature(
        self, doc_id: str, event_id: str, sign_content: str
    ) -> dict:
        url = (
            f"{self.url}/api/v1/outgoing-documents/{doc_id}/events/{event_id}/signature"
        )
        headers = {"Content-Encoding": "base64", "Content-Type": "text/plain"}
        return await self.__request(
            "POST", url, headers=headers, data=sign_content, to_return="text"
        )

    async def accept_document(self, doc_id: str) -> str:
        event = await self.send_incoming_document_event(doc_id)
        event_content = await self.get_incoming_document_event_content(
            doc_id, event["id"]
        )
        log_dir = Path(self.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_path = log_dir / event["id"]
        sign_content = await cryptoPro.sign_detach_file(file_path, event_content)
        await self.send_incoming_document_event_signature(
            doc_id, event["id"], sign_content
        )

    async def get_incoming_document_print(self, doc_id: str) -> bytes:
        url = f"{self.url}/api/v1/incoming-documents/{doc_id}/print"
        return await self.__request("GET", url, to_return="bytes")

    async def get_outgoing_document_print(self, doc_id: str) -> bytes:
        url = f"{self.url}/api/v1/outgoing-documents/{doc_id}/print"
        return await self.__request("GET", url, to_return="bytes")

    async def save_to_redis(self, rds: RedisConnection) -> None:
        await rds.set_cls(self.__class__.__name__, self.__dict__)

    @classmethod
    async def load_from_redis(cls, rds: RedisConnection):
        """
        Загружает состояние объекта
        """
        objcls = await rds.get_cls(cls.__name__)
        if objcls is None:
            raise ValueError("Отсутствует созданный EdoLite объект")
        edolite = cls(**objcls)
        if (
            (edolite._end_date_token is None)
            or (datetime.now() > datetime.fromtimestamp(edolite._end_date_token))
            or (edolite.token is None)
        ):
            await edolite.create_token()
        return edolite


async def test():
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJwcm9kdWN0X2dyb3VwX2luZm8iOlt7Im5hbWUiOiJuYWJlZXIiLCJzdGF0dXMiOiIxMCIsInR5cGVzIjpbIlJFVEFJTCIsIlRSQURFX1BBUlRJQ0lQQU5UIl19LHsibmFtZSI6ImJlZXIiLCJzdGF0dXMiOiI1IiwidHlwZXMiOlsiUkVUQUlMIiwiVFJBREVfUEFSVElDSVBBTlQiXX0seyJuYW1lIjoid2F0ZXIiLCJzdGF0dXMiOiI1IiwidHlwZXMiOlsiUkVUQUlMIiwiVFJBREVfUEFSVElDSVBBTlQiXX0seyJuYW1lIjoibWlsayIsInN0YXR1cyI6IjUiLCJ0eXBlcyI6WyJSRVRBSUwiLCJUUkFERV9QQVJUSUNJUEFOVCJdfSx7Im5hbWUiOiJ0b2JhY2NvIiwic3RhdHVzIjoiNSIsInR5cGVzIjpbIlJFVEFJTCIsIlRSQURFX1BBUlRJQ0lQQU5UIl19LHsibmFtZSI6Im5jcCIsInN0YXR1cyI6IjUiLCJ0eXBlcyI6WyJSRVRBSUwiLCJUUkFERV9QQVJUSUNJUEFOVCJdfV0sInVzZXJfc3RhdHVzIjoiQUNUSVZFIiwiaW5uIjoiMTY0MjAxMTIzNzg3IiwicGlkIjo1NzIzMjI4NzYsImNsaWVudF9pZCI6ImNycHQtc2VydmljZSIsInBvYV9udW1iZXIiOiIzNGJkZGEwMS0wMTdiLTRmYjAtODNjZi0xMmM4MzEyZTNkNmUiLCJhdXRob3JpdGllcyI6WyJST0xFX0FETUlOIiwiQ1JQVC1GQUNBREUuUFJPRklMRS1DT05UUk9MTEVSLkNPTVBBTlkuQ1JFQVRFIiwiQ1JQVC1GQUNBREUuRE9DLUNPTlRST0xMRVIuQ0lTX0lORk9STUFUSU9OX0NIQU5HRS5DUkVBVEUiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5SRUFHR1JFR0FUSU9OLlJFQUQiLCJDUlBULUZBQ0FERS5BUFAtVVNFUi1DT05UUk9MTEVSLkxJU1QtQUNUSVZFLlJFQUQiLCJDUlBULUtNLU9SREVSUy5PUkRFUi1GQUNBREUtQ09OVFJPTExFUi5SRUFESU5HLUJZLU9QRVJBVE9SLlJFQUQiLCJDUlBULUxLLURPQy1BUEkuQVBQLVVTRVItQ09OVFJPTExFUi5XUklURSIsIkNSUFQtTEstRE9DLUFQSS5CTE9DS0lORy1DT05UUk9MTEVSLkNSRUFURSIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLkxLX0dUSU5fUkVDRUlQVF9DQU5DRUwuUkVBRCIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLk9TVF9DT01QTEVURV9ERVNDUklQVElPTi5DUkVBVEUiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5XUklURS1PRkYuQ1JFQVRFIiwiQ1JQVC1GQUNBREUuRE9DLUNPTlRST0xMRVIuQ09OVFJBQ1QtQ09NTUlTU0lPTklORy5DUkVBVEUiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5JTkRJVklEVUFMSVpBVElPTi5DUkVBVEUiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5PU1RfREVTQ1JJUFRJT04uUkVBRCIsIkRPQy1DT05UUk9MTEVSLkdSQVlfWk9ORV9DU1YuQ1JFQVRFIiwiTU9ELUlORk8uTU9ELkRFTEVURSIsIkNSUFQtRkFDQURFLkNJUy1DT05UUk9MTEVSLlNFQVJDSC5SRUFEIiwiQ1JQVC1GQUNBREUuRE9DLUNPTlRST0xMRVIuV1JJVEUtT0ZGLlJFQUQiLCJDUlBULUtNLU9SREVSUy5MQUJFTC1URU1QTEFURS1GQUNBREUtQ09OVFJPTExFUi5VUERBVElORy5XUklURSIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLlNISVAtQ1JPU1NCT1JERVIuQ1JFQVRFIiwiQ1JQVC1GQUNBREUuRE9DLUNPTlRST0xMRVIuTFBfQ0FOQ0VMX1NISVBNRU5UX0NST1NTQk9SREVSLkNSRUFURSIsIkNSUFQtS00tT1JERVJTLk9SREVSLUZBQ0FERS1DT05UUk9MTEVSLlJFQURJTkctQlktU1VaLlJFQUQiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5DQU5DRUwtU0hJUE1FTlQuQ1JFQVRFIiwiQ1JQVC1LTS1PUkRFUlMuT1JERVItRkFDQURFLUNPTlRST0xMRVIuT1JERVJTLUZST00tU1VaLkNSRUFURSIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLktNLUNBTkNFTC5DUkVBVEUiLCJDUlBULUxLLURPQy1BUEkuQVBQLVVTRVItQ09OVFJPTExFUi5DUkVBVEUiLCJDUlBULUtNLU9SREVSUy5MQUJFTC1URU1QTEFURS1GQUNBREUtQ09OVFJPTExFUi5ET1dOTE9BRElORy5ET1dOTE9BRCIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLlJFUE9SVF9SRVdFSUdISU5HLkNSRUFURSIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLlJFQUdHUkVHQVRJT04uQ1JFQVRFIiwiQ1JQVC1GQUNBREUuRE9DLUNPTlRST0xMRVIuTFBfUkVUVVJOLlJFQUQiLCJDUlBULUtNLU9SREVSUy5TVVotUkVHSVNUUlktRkFDQURFLUNPTlRST0xMRVIuUkVBRElORy1CWS1PUEVSQVRPUi5SRUFEIiwiQ1JQVC1GQUNBREUuRE9DLUNPTlRST0xMRVIuTEtfR1RJTl9SRUNFSVBULkNSRUFURSIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLkxLX0dUSU5fUkVDRUlQVF9DQU5DRUwuQ1JFQVRFIiwiQ1JQVC1LTS1PUkRFUlMuTEFCRUwtVEVNUExBVEUtRkFDQURFLUNPTlRST0xMRVIuVVBEQVRJTkctREVGQVVMVC5XUklURSIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLkNJU19OT1RJQ0UuQ1JFQVRFIiwiQ1JQVC1MSy1ET0MtQVBJLlJFU1VNRS1BQ0NFU1MtQ09OVFJPTExFUi5DUkVBVEUiLCJDUlBULUtNLU9SREVSUy5MQUJFTC1URU1QTEFURS1GQUNBREUtQ09OVFJPTExFUi5ERUxFVElORy5ERUxFVEUiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5LTS1BUFBMSUVELUNBTkNFTC5DUkVBVEUiLCJDUlBULUtNLU9SREVSUy5MQUJFTC1URU1QTEFURS1GQUNBREUtQ09OVFJPTExFUi5DUkVBVElORy1ERUZBVUxULkNSRUFURSIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLklORElWSURVQUxJWkFUSU9OLlJFQUQiLCJDUlBULUtNLU9SREVSUy5MQUJFTC1URU1QTEFURS1GQUNBREUtQ09OVFJPTExFUi5TVEFUVVMtQ0hBTkdFLldSSVRFIiwiQ1JQVC1GQUNBREUuRE9DLUNPTlRST0xMRVIuQ1JPU1NCT1JERVItQUNDRVBUQU5DRS5DUkVBVEUiLCJDUlBULUtNLU9SREVSUy5PUEVSQVRPUi5XUklURSIsIkNSUFQtS00tT1JERVJTLkxBQkVMLVRFTVBMQVRFLUZBQ0FERS1DT05UUk9MTEVSLlJFQURJTkctREVGQVVMVFMtQlktU1VaLlJFQUQiLCJDUlBULUtNLU9SREVSUy5PUkRFUi1GQUNBREUtQ09OVFJPTExFUi5SRUFESU5HLlJFQUQiLCJFTEstUkVHSVNUUkFUSU9OLldSSVRFIiwiQ1JQVC1LTS1PUkRFUlMuUEFSVElDSVBBTlQtT1ItT1BFUkFUT1IuUkVBRCIsIkNSUFQtS00tT1JERVJTLkxBQkVMLVRFTVBMQVRFLUZBQ0FERS1DT05UUk9MTEVSLlJFQURJTkctQlktU1VaLlJFQUQiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5FQVMtQ1JPU1NCT1JERVItRVhQT1JULkNSRUFURSIsIkNSUFQtS00tT1JERVJTLlNVWi5XUklURSIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLk9TVF9ERVNDUklQVElPTi5DUkVBVEUiLCJDUlBULUxLLURPQy1BUEkuRFJBRlQuQURNSU5JU1RSQVRJT04iLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5TSElQLUNST1NTQk9SREVSLlJFQUQiLCJDUlBULUtNLU9SREVSUy5MQUJFTC1URU1QTEFURS1GQUNBREUtQ09OVFJPTExFUi5ERUxFVElORy1ERUZBVUxULkRFTEVURSIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLlNISVBNRU5ULkNSRUFURSIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLkxPQU4uQ1JFQVRFIiwiQ1JQVC1LTS1PUkRFUlMuT1JERVItRkFDQURFLUNPTlRST0xMRVIuU1VaLUVWRU5UUy5DUkVBVEUiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5SRUNFSVBULkNSRUFURSIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLkRJU0FHR1JFR0FUSU9OLlJFQUQiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5MUF9JTlRST0RVQ0VfT1NULkNSRUFURSIsIkVMSy1SRUdJU1RSQVRJT04uQ1JFQVRFIiwiQ1JQVC1GQUNBREUuRE9DLUNPTlRST0xMRVIuTEtfR1RJTl9SRUNFSVBULlJFQUQiLCJDUlBULUZBQ0FERS5DSVMtQ09OVFJPTExFUi5SRVBPUlQuRE9XTkxPQUQiLCJDUlBULUZBQ0FERS5BUFAtVVNFUi1DT05UUk9MTEVSLkxJU1QtUkVNT1ZFRC5SRUFEIiwiQ1JQVC1GQUNBREUuRE9DLUNPTlRST0xMRVIuQ1JPU1NCT1JERVIuUkVBRCIsIkNSUFQtTEstRE9DLUFQSS5BUFAtVVNFUi1DT05UUk9MTEVSLkRFTEVURSIsIkNSUFQtS00tT1JERVJTLkxBQkVMLVRFTVBMQVRFLUZBQ0FERS1DT05UUk9MTEVSLkRPV05MT0FESU5HLUJZLU9QRVJBVE9SLkRPV05MT0FEIiwiQ1JQVC1GQUNBREUuRE9DLUNPTlRST0xMRVIuQUdHUkVHQVRJT04uUkVBRCIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLkNST1NTQk9SREVSLkNSRUFURSIsIkNSUFQtS00tT1JERVJTLk9SREVSLUZBQ0FERS1DT05UUk9MTEVSLkNSRUFUSU5HLURSQUZULkNSRUFURSIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLlJFTUFSS0lORy5SRUFEIiwiQ1JQVC1GQUNBREUuRE9DLUNPTlRST0xMRVIuSU5ESS1DT01NSVNTSU9OSU5HLkNSRUFURSIsIkNSUFQtS00tT1JERVJTLlNUQVRJU1RJQ1MtRkFDQURFLUNPTlRST0xMRVIuUkVBRElORy1QQVJUSUNJUEFOVC1TVEFUSVNUSUNTLlJFQUQiLCJFTEstUFJPRklMRS5SRUFEIiwiQ1JQVC1GQUNBREUuRE9DLUNPTlRST0xMRVIuQ09OTkVDVF9UQVAuQ1JFQVRFIiwiQ1JQVC1GQUNBREUuRE9DLUNPTlRST0xMRVIuQUNDRVBUQU5DRS5DUkVBVEUiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5MS19SRUNFSVBUX0NBTkNFTC5DUkVBVEUiLCJDUlBULUxLLURPQy1BUEkuQURELUNFUlQtQ09OVFJPTExFUi5DUkVBVEUiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5TSElQTUVOVC5SRUFEIiwiQ1JQVC1GQUNBREUuRE9DLUNPTlRST0xMRVIuRUFTLUNST1NTQk9SREVSLUVYUE9SVC5SRUFEIiwiQ1JQVC1GQUNBREUuTUFSS0VELVBST0RVQ1RTLUNPTlRST0xMRVIuUkVBRCIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLkFHR1JFR0FUSU9OLkNSRUFURSIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLkRJU0FHR1JFR0FUSU9OLkNSRUFURSIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLkNPTU1JU1NJT05JTkcuQ1JFQVRFIiwiQ1JQVC1GQUNBREUuTUFSS0VELVBST0RVQ1RTLUNPTlRST0xMRVIuQURNSU5JU1RSQVRJT04iLCJDUlBULUtNLU9SREVSUy5QQVJUSUNJUEFOVC5XUklURSIsIkNSUFQtS00tT1JERVJTLkxBQkVMLVRFTVBMQVRFLUZBQ0FERS1DT05UUk9MTEVSLkNSRUFUSU5HLkNSRUFURSIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLkNST1NTQk9SREVSLUVYUE9SVC5DUkVBVEUiLCJDUlBULUtNLU9SREVSUy5PUkRFUi1GQUNBREUtQ09OVFJPTExFUi5DUkVBVElORy5DUkVBVEUiLCJDUlBULUZBQ0FERS5QUk9GSUxFLUNPTlRST0xMRVIuQ09NUEFOWS5SRUFEIiwiQ1JQVC1GQUNBREUuUEFSVElDSVBBTlQtQ09OVFJPTExFUi5HRVQtQlktSU5OLlJFQUQiLCJMSUNFTlNFLUVRVUlQTUVOVC1SRUdJU1RSWS5SRUFEIiwiRUxLLVJFR0lTVFJBVElPTi5SRUFEIiwiQ1JQVC1LTS1PUkRFUlMuT1JERVItRkFDQURFLUNPTlRST0xMRVIuTU9ESUZZSU5HLURSQUZULldSSVRFIiwiQ1JQVC1LTS1PUkRFUlMuUEFSVElDSVBBTlQtT1ItT1BFUkFUT1IuV1JJVEUiLCJMSUNFTlNFLUVRVUlQTUVOVC1SRUdJU1RSWS5BRE1JTklTVFJBVElPTiIsIkNSUFQtS00tT1JERVJTLkxBQkVMLVRFTVBMQVRFLUZBQ0FERS1DT05UUk9MTEVSLlJFQURJTkctQlktT1BFUkFUT1IuUkVBRCIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLkxQX0NBTkNFTF9TSElQTUVOVF9DUk9TU0JPUkRFUi5SRUFEIiwiQ1JQVC1GQUNBREUuRE9DLUNPTlRST0xMRVIuQUNDRVBUQU5DRS5SRUFEIiwiQ1JQVC1GQUNBREUuRE9DLUNPTlRST0xMRVIuT1NUX0NPTVBMRVRFX0RFU0NSSVBUSU9OLlJFQUQiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5MUF9JTlRST0RVQ0VfT1NULlJFQUQiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5SRVBPUlRfUkVXRUlHSElORy5SRUFEIiwiQ1JQVC1GQUNBREUuQ0lTLUNPTlRST0xMRVIuUkVQT1JULlJFQUQiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5JTVBPUlQtQ09NTUlTU0lPTklORy5DUkVBVEUiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5SRU1BUktJTkcuQ1JFQVRFIiwiQ1JQVC1LTS1PUkRFUlMuU1VaLVJFR0lTVFJZLUZBQ0FERS1DT05UUk9MTEVSLlJFQURJTkcuUkVBRCIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLkxPQU4uUkVBRCIsIkNSUFQtRkFDQURFLkRPQy1DT05UUk9MTEVSLkxQX1JFVFVSTi5DUkVBVEUiLCJDUlBULUtNLU9SREVSUy5MQUJFTC1URU1QTEFURS1GQUNBREUtQ09OVFJPTExFUi5SRUFESU5HLlJFQUQiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5DT01NSVNTSU9OSU5HLlJFQUQiLCJDUlBULUtNLU9SREVSUy5PUkRFUi1GQUNBREUtQ09OVFJPTExFUi5NT0RJRllJTkcuV1JJVEUiLCJDUlBULUZBQ0FERS5ET0MtQ09OVFJPTExFUi5DUk9TU0JPUkRFUi1FWFBPUlQuUkVBRCIsIlJPTEVfT1JHX1JFVEFJTCIsIlJPTEVfT1JHX1RSQURFX1BBUlRJQ0lQQU5UIiwiSU5OXzE2NDIwMTEyMzc4NyJdLCJmdWxsX25hbWUiOiLQmtCw0LvRjNC90LjRhtC60LjQuSDQnNC40YXQsNC40Lsg0J7Qu9C10LPQvtCy0LjRhyIsInNjb3BlIjpbInRydXN0ZWQiXSwibWNoZF9pZCI6MTMwMDAwOTM1MTEsImlkIjoxNDAwMDMwNjAxOSwiZXhwIjoxNzM4MTg3NTUyLCJvcmdhbmlzYXRpb25fc3RhdHVzIjoiUkVHSVNURVJFRCIsImp0aSI6IjIzMzRlZDQyLTE1MmEtNDZlZi1hMzMzLWJkNWI1YWFjOGNhMiJ9.PlG9_YUy6ueEEP2JCEgxqJOdfrzuG-e58rmHeSZ43rY"
    doc_id = "732706de-e1a8-4f07-964b-7a9ed1964ee5"
    edo = EdoLite(token=token)
    print(await edo.accept_document(doc_id))


if __name__ == "__main__":
    import asyncio

    asyncio.run(test())
