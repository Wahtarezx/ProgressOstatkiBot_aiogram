#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import sys
import time
import uuid
from collections import namedtuple

from core.services.markirovka.pd_models.tovar_groups import TovarGroup

sys.path.append("/home/zabbix/ProgressOstatkiBot_aiogram")
import config

#
# sys.path.append(config.dir_path)

from core.services.markirovka.cryptopro import CryproPro

# from cryptopro import CryproPro
import requests
from urllib.parse import urlencode
from base64 import b64encode
from datetime import datetime
import xml.etree.ElementTree as ET
from loguru import logger


def check_error(response):
    response = json.loads(response)
    if response.get("error") is not None or response.get("errors") is not None:
        raise ConnectionError(response)
    return response


def get_status_name_from_ofd(name):
    path = os.path.join(
        config.dir_path,
        "core",
        "services",
        "markirovka",
        "static",
        "json",
        "ofd",
        "statuses.json",
    )
    with open(path, "r", encoding="utf-8") as f:
        status_map = json.loads(f.read())
    return status_map.get(str(name).lower(), "Неизвестно")


async def get_pg_info(group_name: str) -> TovarGroup:
    """
    Возвращает информацию о товарной группе по её названию
    :param group_name: Название товарной группы
    :return: dict
    """
    path = os.path.join(
        config.dir_path,
        "core",
        "services",
        "markirovka",
        "static",
        "json",
        "tovar_groups.json",
    )
    with open(path, "r", encoding="utf-8") as f:
        tovar_group_maps = json.loads(f.read())
    return TovarGroup.model_validate_json(json.dumps(tovar_group_maps.get(group_name)))


class OFD:
    def __init__(
        self, inn: str = None, pin: str = "", thumbprint: str = None, token: str = None
    ):
        """
        :param inn: ИНН сертификата
        :param pin: ПИН сертификата. По умолчанию пуст
        """
        self.thumbprint = thumbprint
        if os.name == "posix":
            self.cryproPro = CryproPro(pin=pin, thumbprint=thumbprint)
        self.inn = inn
        self.token = self.create_token()["access_token"] if token is None else token

    # region requests
    def get(self, url, args=None, headers=None):
        url = f"{url}?{urlencode(args)}" if not args is None else f"{url}"
        headers = (
            {"Authorization": f"Bearer {self.token}"}
            if headers is None
            else {"Authorization": f"Bearer {self.token}", **headers}
        )
        response = requests.request("GET", url, headers=headers)
        return response.text

    def post(self, url, args=None, data=None, headers=None):
        url = f"{url}" if args is None else f"{url}?{urlencode(args)}"
        data = "" if data is None else data
        headers = (
            {"Authorization": f"Bearer {self.token}"}
            if headers is None
            else {"Authorization": f"Bearer {self.token}", **headers}
        )
        response = requests.post(url, headers=headers, data=data)

        return response.text

    def put(self, url, args=None, data=None, headers=None):
        url = f"{url}" if args is None else f"{url}?{urlencode(args)}"
        data = "" if data is None else data
        headers = (
            {"Authorization": f"Bearer {self.token}"}
            if headers is None
            else {"Authorization": f"Bearer {self.token}", **headers}
        )
        response = requests.put(url, headers=headers, data=data)
        return response.text

    # endregion

    def create_token(self):
        url = f"https://edo.platformaofd.ru/security/public/api/v3/oauth/token"

        sign_content = json.dumps({"ts": int(time.time()), "nonce": str(uuid.uuid4())})
        # sign_content = f'"ts" : {str(datetime.now().timestamp()).split(".")[0]}, "nonce" : "{str(uuid.uuid4())}"'
        # print(sign_content)
        signing = self.cryproPro.signing_data(b64encode(sign_content.encode()).decode())
        signing = signing.replace("\r\n", "")
        payload = urlencode({"grant_type": "signature", "signature": signing})
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "x-client-id": str(uuid.uuid4()),
        }
        r = requests.post(url, headers=headers, data=payload).json()
        if r.get("error", False):
            if (
                "No user by certificate or snils. Please ensure you use proper keys"
                in r.get("error_description")
            ):
                raise ConnectionError("В личном кабинете ЭДО нужно добавить сертификат")
        return r

    def check_profile_certificate(self):
        r = self.create_token().json()
        error = r.get("error_description")
        if error is not None:
            if (
                "No user by certificate or snils. Please ensure you use proper keys"
                in error
            ):
                raise ConnectionError(
                    "У данного пользователя при регистрации не указали СНИЛС.\n"
                    "Нужно в личном кабинете ЭДО добавить его сертификат\n"
                    "Видео как добавить сертификат: https://drive.google.com/file/d/1vEbgKbaZXPly33B4Co0vDTUMDfXywh3J/view?usp=sharing"
                )

    async def get_doc_type(self, doc: dict):
        type_mappings = {
            "ON_NSCHFDOPPR": "Универсальный передаточный документ (УПД)",
            "ON_NSCHFDOPPOK": "Универсальный передаточный документ (УПД)",
            "ON_NKORSCHFDOPPR": "Универсальный корректирующий документ (УКД)",
            "ON_NKORSCHFDOPPOK": "Универсальный корректирующий документ (УКД)",
            "DP_TOVTORGPR": "Товарная накладная (ТОРГ-12)",
            "DP_TOVTORGPOK": "Товарная накладная (ТОРГ-12)",
            "DP_REZRUISP": "Акт выполненных работ/оказанных услуг",
            "DP_REZRUZAK": "Акт выполненных работ/оказанных услуг",
            "DP_PRIRASXPRIN": "ТОРГ-2",
            "DP_PRIRASXDOP": "ТОРГ-2",
            "DP_PDOTPR": "Подтверждение даты отправки",
            "DP_PDPOL": "Подтверждение даты получения",
            "SENDING_FAILURE_ACK": "Квитанция «Ошибка отправки»",
            "DP_IZVPOL": "Извещение о получении (ИОП)",
            "DP_UVUTOCH": "Уведомление об уточнении (УОУ)",
            "DP_PRANNUL": "Предложение об аннулировании (ПОА)",
        }

        doc_type = type_mappings.get(doc.get("type"), "Акт сверки")
        return doc_type

    def find_subscribers(self, inn):
        url = "https://edo.platformaofd.ru/subscriber/public/api/v3/subscribers"
        response = json.loads(self.get(url=url, args={"inn": inn}))
        return response

    async def get_doc_info(self, args):
        url = "https://edo.platformaofd.ru/document/public/api/v3/document-flows"
        response = json.loads(self.get(url=url, args=args))
        return response

    async def get_not_accept_documents(self):
        """Получаем не принятые накладные. Документы со статусом SENT и который в slaves[0]['status'] == 'NEW' || 'SENT'"""
        # start_date = datetime.strftime(datetime.now() - timedelta(days=30), '%Y-%m-%d')
        # end_date = datetime.now().strftime('%Y-%m-%d')
        response = await self.get_doc_info({"status": "SENT,ACCEPTED"})
        not_accept_docs = []
        for doc in response:
            if doc.get("status") == "ACCEPTED":
                for slave in doc.get("slaves", []):
                    # if slave['status'] == "SENT" and slave['type'] == 'DP_PDOTPR':
                    #     not_accept_docs.append(doc)
                    if slave["status"] == "NEW" and slave["type"] == "DP_IZVPOL":
                        not_accept_docs.append(doc)
            elif doc.get("status") == "SENT":
                not_accept_docs.append(doc)
        return not_accept_docs

    async def put_notification(self, document):
        url = f'https://edo.platformaofd.ru/document/public/api/v3/documents/{document["id"]}/notification'
        person = "await get_cert_by_tb(self.thumbprint)"
        data = json.dumps(
            {
                "inn": person.inn,
                "person": {
                    "first": person.first_name,
                    "middle": person.patronymic,
                    "last": person.last_name,
                },
                "position": "Б",
            }
        )
        response = self.put(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        return response

    async def get_document_content(self, doc_id):
        url = f"https://edo.platformaofd.ru/document/public/api/v3/documents/{doc_id}/content"
        response = requests.get(
            url,
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
        )
        return response.text

    async def connect_signature_to_doc(self, data, doc_id):
        url = f"https://edo.platformaofd.ru/document/public/api/v4/documents/{doc_id}/signature"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        response = requests.put(url, data=json.dumps({"value": data}), headers=headers)
        return response

    def get_user_info(self, user_id="me"):
        url = f"https://edo.platformaofd.ru/security/public/api/v3/users/{user_id}"
        response = self.get(url)
        return response

    def get_signature_doc(self, doc_id):
        url = f"https://edo.platformaofd.ru/document/public/api/v4/documents/{doc_id}/signature"
        headers = {"Content-Type": "application/json"}
        response = self.get(url, headers=headers)
        return response

    async def create_accept_doc(self, doc):
        url = f'https://edo.platformaofd.ru/document/public/api/v3/documents/{doc["id"]}/acceptance'
        person = "await get_cert_by_tb(self.thumbprint)"
        data = json.dumps(
            {
                "type": "UtdAcceptance",
                "data": datetime.now().strftime("%Y-%m-%d"),
                "signer": {
                    "type": "SP",
                    "status": "ORG_CUSTOMER",
                    "scopeOfAuthority": "TRANSACTION_AND_PROCESSING",
                    "authorityReason": "Должностные обязанности",
                    "inn": person.inn,
                    "orgName": f"{person.last_name} {person.first_name} {person.patronymic}",
                    "name": {
                        "first": person.first_name,
                        "middle": person.patronymic,
                        "last": person.last_name,
                    },
                    "position": "Б",
                },
                "details": {
                    "acceptanceType": "ACCEPTED",
                },
            }
        )
        response = self.put(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        return response

    async def signed_and_connect_document(self, content, doc_id_for_signed, file_path):
        signed_content = self.cryproPro.sign_detach_data(content, file_path)
        return await self.connect_signature_to_doc(signed_content, doc_id_for_signed)

    async def send_notification(self, document, file_path):
        notificaion = json.loads(await self.put_notification(document))
        content = await self.get_document_content(notificaion["id"])
        r = await self.signed_and_connect_document(
            content, notificaion["id"], file_path
        )
        if not r.ok:
            raise ConnectionError(r.text)
        return r

    async def send_accept_doc(self, document, file_path):
        accept = json.loads(await self.create_accept_doc(document))
        content = await self.get_document_content(accept["id"])
        r = await self.signed_and_connect_document(content, accept["id"], file_path)
        if not r.ok:
            raise ConnectionError(r.text)
        return r

    async def accept_document(self, document, file_path):
        #  Если пришел документ с типом "UNFORMALIZED" и SENT,
        #  то нужно взять контент (в нём нет slaves, берём основной ID) подписать и отправить,
        #  затем отправить ИОП, взять контент, подписать

        # Акт сверки
        if document["type"] == "UNFORMALIZED":
            content = await self.get_document_content(document["id"])
            await self.signed_and_connect_document(content, document["id"], file_path)
            r = await self.send_notification(document, file_path)
        # Документ принят, но не подписан ИОП
        elif document["status"] == "ACCEPTED":
            r = await self.send_notification(document, file_path)
        else:
            await self.send_notification(document, file_path)
            r = await self.send_accept_doc(document, file_path)
        return r

    async def get_pdf_doc(self, doc_id, path_to_save):
        url = f"https://edo.platformaofd.ru/document/public/api/v4/documents/{doc_id}/watermarked-content"
        r = requests.get(url)
        with open(path_to_save, "wb") as pdf:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(url, headers=headers, timeout=60)
            pdf.write(response.content)

    async def get_eans_info_from_doc(self, doc_id):
        content = await self.get_document_content(doc_id)
        try:
            doc = ET.fromstring(content)
            # doc = ET.parse('test.xml')
            svedstov = doc.findall("*/*/СведТов")
            EAN = namedtuple("EAN", "name bcode dcode op_mode tmctype measure price")
            result = []
            for svedtov in svedstov:
                name = svedtov.get("НаимТов")
                price = svedtov.get("СтТовУчНал")
                price = "0" if price is None else price
                group_name = svedtov.find("ИнфПолФХЖ2[@Идентиф='ТовГрМарк']")
                group_name = (
                    group_name.get("Значен") if group_name is not None else "lp"
                )
                bcode = svedtov.find("ИнфПолФХЖ2[@Идентиф='штрихкод']")
                if bcode is None:
                    continue
                else:
                    bcode = bcode.get("Значен")

                measure = svedtov.find("ДопСведТов")
                measure = measure.get("НаимЕдИзм") if measure is not None else "шт"
                measure = "1" if measure == "шт" else "2"

                pg = await get_pg_info(group_name)
                if pg is not None:
                    result.append(
                        EAN(
                            name,
                            bcode,
                            pg.dcode,
                            pg.op_mode,
                            pg.tmctype,
                            measure,
                            price,
                        )
                    )

            return result
        except Exception as e:
            logger.debug(str(e))


async def main():
    # token = 'eyJhbGciOiJIUzUxMiIsInppcCI6IkRFRiJ9.eNqsUk1rxCAU_C8eQwSNJkb_xN56KT24zxdq2XygBhaW_vfabBvSQwvJ1oPgwMw8582NvCVPDAFRc10jp7oDS6WQFdWua6nKF_JWqto2pCTeJmJ4o5tWtoLxkuB1yoBiUmnFP4E4n7NcXTGuRCZMGHofox-HSMwzqZ5OlDeVZEJUWnNF2V_HAIbkOw82oXF4wYRZsjDZI0LwZwwmoHUZ26nrRph7HJIp9nM35o-xv0YvTI99fsdXPy1YOU8uf7i8f9isUe502qgemHObPOSpluR3alw84BDx4I5gHJKF9LD7Uf7akbvA91aWDa1d_D_N4wH92qOfBXp5_wAAAP__.9S3HMy2RaIyNu4XMTLy0JjnZ3m2Cydq0u8483356iHM0K5aIDciZoaO_hzUICFLfmFXkPdxNkZJHDeC-Ojk9Gw'
    ofd = OFD(thumbprint="B2B0777BB77AFBA0DB215B0488BFF23B88D8F8F5", token="123")
    print(ofd.create_token().json())
    # print(ofd.cryproPro.certificate_info())
    # print(ofd.create_token())
    # print(str(uuid.uuid4()))
    # pprint(ofd.get_eans_info_from_doc('41722492'))
    # not_accept_docs = ofd.get_not_accept_documents()
    # print(f'Нашел накладных {len(not_accept_docs)}')
    # url = 'https://edo.platformaofd.ru/document/public/api/v3/document-flows'
    # not_accept_docs = json.loads(ofd.get(url=url,
    #                                args={
    #                                    'status': 'SENT,ACCEPTED',
    #                                    'page_size': '50'
    #                                }))
    # for doc in not_accept_docs:
    #     if doc['type'] != 'UNFORMALIZED':
    #         eans = ofd.get_eans_info_from_doc(doc['id'])
    #         print(doc['id'], len(eans) if eans is not None else '')

    # print(ofd.find_subscribers(162403329917))
    # doc_id = 41123374
    # ofd.put_notification(doc_id, )
    # ofd.connect_signature_to_doc(
    #     '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',
    #     doc_id)
    # print(ofd.get_user_info('2VO-162403329917-00000000000000000000000000000'))
    # with open(r'C:\Users\User\Desktop\test.xml', 'wb') as f:
    #     f.write(ofd.get_document_content(doc_id).encode('windows-1251'))

    # root = ET.fromstring(ofd.get_document_content(doc_id))
    # tree = ET.ElementTree(root)
    # tree.write(r'C:\Users\User\Desktop\test.xml', encoding='windows-1251')


if __name__ == "__main__":
    # asyncio.run(main())
    print(get_pg_info("tobacco"))
