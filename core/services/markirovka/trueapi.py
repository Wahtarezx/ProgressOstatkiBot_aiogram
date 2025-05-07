#!/usr/bin/env python3.10
# -*- coding: utf-8 -*-
import asyncio
import io
import json
import os
import re
import sys
import zipfile
from collections import namedtuple
from pathlib import Path

from aiogram.client.session import aiohttp
from pydantic import TypeAdapter

from core.services.egais.goods.pd_models import Dcode, OpMode, TmcType
from core.services.markirovka.pd_models.gismt import *
from core.services.markirovka.pd_models.gismt import Product, Balance
from core.utils.cryptopro.cryptopro import cryptoPro
from core.utils.redis import RedisConnection

sys.path.append("/home/zabbix/ProgressOstatkiBot_aiogram")
from core.services.markirovka.ostatki.models import OstatkiExcel

import config
from core.services.markirovka.utils.operation_with_csv import (
    write_volume_balance,
    parse_ostatki_csv,
)

from core.services.markirovka.ofdplatforma import get_pg_info
import requests
from base64 import b64encode
from datetime import datetime, timedelta
from core.loggers.make_loggers import znak_log, bot_log


def log_request(method: str, url: str, headers: dict = None, data: str = None) -> None:
    log = znak_log.bind(url=url, headers=headers, data=data)
    log.info(f"{method} {url}")


def log_response(response: requests.Response) -> None:
    log = znak_log.bind(status_code=response.status_code, url=response.url)
    if response.ok:
        log.success(response.text)
    else:
        log.error(response.text)


def get_ean_from_gtin(gtin: str):
    if gtin is not None:
        return re.findall(r"0*([0-9]+)", gtin)[0]


def check_error(response: str, text: bool = False) -> dict | str:
    try:
        check_r = json.loads(response)
        if check_r.get("error") is not None:
            r = check_r.get("error")
        elif check_r.get("errors") is not None:
            r = check_r.get("errors")
        elif check_r.get("error_message") is not None:
            r = check_r.get("error_message")
        else:
            r = None
        if r is not None:
            raise ZnakAPIError(r)
    except json.decoder.JSONDecodeError:
        check_r = response
    return response if text else check_r


def get_doctype_name(code):
    path = os.path.join(
        config.dir_path,
        "core",
        "services",
        "markirovka",
        "static",
        "json",
        "znak",
        "doctype.json",
    )
    with open(path, "r", encoding="utf-8") as f:
        docname_maps = json.loads(f.read())
    return docname_maps.get(code, code)


def get_status_name(code):
    path = os.path.join(
        config.dir_path,
        "core",
        "services",
        "markirovka",
        "static",
        "json",
        "znak",
        "statuses.json",
    )
    with open(path, "r", encoding="utf-8") as f:
        status_map = json.loads(f.read())
    return status_map.get(str(code), "Неизвестно")


def get_actions(is_volume_balance: bool):
    path = os.path.join(
        config.dir_path,
        "core",
        "services",
        "markirovka",
        "static",
        "json",
        "znak",
        "actions.json",
    )
    with open(path, "r", encoding="utf-8") as f:
        actions = json.loads(f.read())
    if is_volume_balance:
        return actions["volume"]
    return actions["mark"]


async def ean13info(eans: list) -> list:
    EAN = namedtuple("EAN", "name ean dcode op_mode tmctype")
    info = []
    for ean in eans:
        ean = ean[1:] if ean.startswith("0") else ean
        r = requests.get(
            f"https://mobile.api.crpt.ru/mobile/check?code={ean}&codeType=ean13"
        ).json()
        cat_name = r["catalogData"][0]["categories"][0]["cat_name"]
        productName = r["productName"]
        if cat_name in ["Молочная продукция", "Упакованная вода"]:
            dcode = Dcode.markirovka
            op_mode = OpMode.basic
            tmctype = TmcType.markedgoods
        elif cat_name == "Табачная продукция":
            dcode = Dcode.tobacco
            op_mode = OpMode.tobacco
            tmctype = TmcType.tobacco
        else:
            continue
        info.append(EAN(productName, ean, dcode, op_mode, tmctype))
    return info


class ZnakAPIError(Exception):
    pass


class TrueApiRedisError(Exception):
    pass


class TrueApi:
    def __init__(
            self,
            pin: str = "",
            token: str = None,
            thumbprint: str = None,
            inn_to_auth: str = None,
            **kwargs,
    ):
        """
        :param inn_to_auth: ИНН сертификата
        :param pin: ПИН сертификата. По умолчанию пуст
        :param token: Токен сертификата. По умолчанию None
        """
        self.true_api_v3 = "https://markirovka.crpt.ru/api/v3/true-api"
        self.true_api_v4 = "https://markirovka.crpt.ru/api/v4/true-api"
        self.edoLite_url = "https://edo-gismt.crpt.ru"
        self.thumbprint = thumbprint
        self.token = token
        self._end_date_token: float = kwargs.get("_end_date_token")
        self.permissive_token = None
        self.inn_to_auth = inn_to_auth

    async def __request(
            self,
            method: str,
            url: str,
            params: dict = None,
            headers: dict = None,
            data: dict = None,
            jsons: dict = None,
            to_return: str = "json",
    ) -> str | dict | bytes:
        znak_log.bind(url=url, headers=headers, data=data).info(f"{method} {url}")
        headers = (
            {"Authorization": f"Bearer {self.token}"}
            if headers is None
            else {"Authorization": f"Bearer {self.token}", **headers}
        )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                        method, url, params=params, headers=headers, data=data, json=jsons
                ) as response:
                    log = znak_log.bind(status_code=response.status, url=response.url)
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
                        error_dict = await response.json()
                        error_msg = error_dict.get("error_message", "")
                        if (
                                "В параметре inn должен быть передан ИНН организации"
                                in error_msg
                        ):
                            raise ZnakAPIError(
                                "С данным ИНН нет оформленных доверенностей (МЧД)"
                            )
                        elif "Отсутствуют доверенности" in error_msg:
                            raise ZnakAPIError(
                                "С данным ИНН нет оформленных доверенностей (МЧД)"
                            )
                        raise ZnakAPIError(error_text, response.status)
        except aiohttp.ClientError as e:
            znak_log.error(f"HTTP request failed: {e}")
            raise

    # region Login
    async def simple_signin(self, uuid: str, signing: str, inn: str) -> str:
        """
        Логинимся в ЧЗ
        :param inn: ИНН участника у которого оформлена доверенность на config.main_thumbprint
        :param uuid:
        :param signing: Подписанная data
        :return: Токен авторизации
        """
        url = f"{self.true_api_v3}/auth/simpleSignIn"
        headers = {"Content-Type": "application/json", "accept": "application/json"}
        data = (
            {"uuid": uuid, "data": signing}
            if inn is None
            else {"uuid": uuid, "data": signing, "inn": inn}
        )
        response = await self.__request(
            "POST", url, headers=headers, data=json.dumps(data)
        )
        return response["token"]

    async def create_token(self, inn: str = None):
        """Создание токена"""
        if inn is None:
            inn = self.inn_to_auth
        login_data = await self.get_uuid_and_data()
        signing = await cryptoPro.sign_attach_data(login_data["data"])
        self.token = await self.simple_signin(login_data["uuid"], signing, inn)
        self._end_date_token = (datetime.now() + timedelta(hours=12)).timestamp()

    async def get_uuid_and_data(self) -> dict:
        """Начало авторизации. Получение uuid и data"""
        headers = {"accept": "application/json"}
        url = f"{self.true_api_v3}/auth/key"
        return await self.__request("GET", url, headers=headers)

    # region True api
    async def get_doc_list(self, args) -> dict:
        """
        Список всех документов (Метод получения списка загруженных документов в ГИС МТ)
        :param args: urlencode. Обязательный памераметр pg
        :return: Список документов
        """
        return await self.__request(
            "GET", f"{self.true_api_v4}/doc/list", args, self.token
        )

    async def get_KI_info(self, group_id: GroupIds) -> CreateTask:
        """
        Создаёт выгрузку актуального баланса остатков, у которых учёт ведется "Экземплярный по кодам маркировки"
        8.1.3. Получение списка КИ участника оборота товаров по заданному фильтру
        :return: json ответ в котором есть task_id, чтобы скачать выгрузку
        """
        url = f"{self.true_api_v3}/dispenser/tasks"
        data = json.dumps(
            {
                "format": "CSV",
                "name": "FILTERED_CIS_REPORT",
                "periodicity": "SINGLE",
                "productGroupCode": group_id.value,
                "params": '{"participantInn":"'
                          + self.inn_to_auth
                          + '","packageType":["UNIT", "LEVEL1"],"status":"INTRODUCED"}',
            }
        )
        return CreateTask.model_validate_json(
            await self.__request(
                "POST",
                url=url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
        )

    async def task_info(self, task_id: str, pg: GroupIds = None) -> TaskInfo:
        """8.2. Метод получения статуса задания на выгрузку"""
        url = f"{self.true_api_v3}/dispenser/tasks/{task_id}"
        r = await self.__request(
            "GET", url=url, params={"pg": pg.value} if pg is not None else None
        )
        return TypeAdapter(TaskInfo).validate_python(r)

    async def get_user_info(self, inn=None) -> Participants:
        if inn is None:
            inn = self.inn_to_auth
        url = f"{self.true_api_v3}/participants?inns={inn}"
        return TypeAdapter(Participants).validate_python(
            (await self.__request("GET", url))[0]
        )

    async def profile_info(self) -> ProfileEdoInfo:
        """Функция не с офф документации"""
        url = f"https://markirovka.crpt.ru/api/v3/facade/profile/edo/get"
        return TypeAdapter(ProfileEdoInfo).validate_python(
            await self.__request("GET", url, headers={"Accept": "application/json"})
        )

    async def get_dispensers(self, task_id: list = None) -> DispensersResults:
        """8.4 Метод получения результирующих ID выгрузок данных"""
        url = f"{self.true_api_v3}/dispenser/results"
        params = (
            {"page": 0, "size": 50, "task_ids": task_id}
            if task_id is not None
            else {"page": 0, "size": 50}
        )
        return TypeAdapter(DispensersResults).validate_python(
            await self.__request("GET", url, params)
        )

    async def get_dispenser_results(
            self,
            page: int = 0,
            size: int = 20,
            pg: GroupIds = None,
            task_ids: str = None,
    ) -> DispensersResults:
        url = f"{self.true_api_v3}/dispenser/results"
        args = {"page": page, "size": size}

        if pg is not None:
            args["pg"] = pg.value
        if task_ids is not None:
            args["task_ids"] = task_ids
        return TypeAdapter(DispensersResults).validate_python(
            await self.__request("GET", url, args)
        )

    async def get_dispenser_file(self, taskId: str, dir_path: Path) -> list[Path]:
        """
        Метод предоставляет возможность скачивания выгрузки в статусе «COMPLETED»
        8.5. Метод получения ZIP-файла выгрузки
        :param taskId: id выгрузки
        :param dir_path: Папка куда будез распакован архив
        :return: Путь до распакованных файлов
        """
        url = f"{self.true_api_v3}/dispenser/results/{taskId}/file"
        content_response = await self.__request("GET", url, to_return="content")
        z = zipfile.ZipFile(io.BytesIO(content_response))
        dir_path.mkdir(parents=True, exist_ok=True)
        z.extractall(str(dir_path))
        return [dir_path / p for p in z.namelist()]

    async def send_KI_info_dispensers(self, product_groups: list) -> list[CreateTask]:
        """
        Отправляет выгрузки КИ(кроме молока, воды, антисептика), чтобы узнать актуальный баланс клиента
        :return: Возращает список [dispensers(task_id, group_id), ...] по которому можно скачать выгрузку
        """
        result = []
        # Цикл по категориям товара профиля
        for gn in product_groups:
            pg = await get_pg_info(gn)
            if pg is None:
                raise ValueError(
                    f'Не найдено ни одной группы с данным названием "{gn}"'
                )
            if gn in ["water", "antiseptic", "milk", "bio"]:
                continue
            result.append(self.get_KI_info(pg.group_id))
        return result

    async def wait_dispensers(
            self, createTasks: list[CreateTask], response_wait: int = 10
    ) -> list[TaskInfo]:
        if not createTasks:
            return []
        while True:
            await asyncio.sleep(response_wait)
            wait_task = 0
            result = []
            for createTask in createTasks:
                task = await self.task_info(createTask.id, createTask.productGroupCode)
                if task.currentStatus == TaskCreateStatus.PREPARATION:
                    wait_task += 1
                else:
                    result.append(task)
                response_wait += 5
            if wait_task == 0:
                return result

    async def document_create(
            self,
            pg_name: str,
            product_document: str,
            doctype: GisMtDocType,
            file_path: str,
            document_format: str = "MANUAL",
    ) -> str:
        """
        4.1. Единый метод создания документов
        :param pg_name: Товарная группа
        :param product_document: Тело формируемого документа
        :param doctype: Код типа документа
        :param file_path: Путь до файла который будем подписывать
        :param document_format: Тип документа
        :return: Уникальный идентификатор документа в ГИС МТ
        """
        url = f"{self.true_api_v3}/lk/documents/create"
        data = {
            "document_format": document_format,
            "product_document": b64encode(product_document.encode()).decode(),
            "type": doctype.value,
            "signature": await cryptoPro.sign_detach_file(
                file_path=file_path, content=product_document
            ),
        }
        args = {"pg": pg_name}
        headers = {"Content-Type": "application/json"}
        return await self.__request(
            method="POST",
            url=url,
            params=args,
            data=json.dumps(data),
            headers=headers,
            to_return="text",
        )

    async def get_actual_balance(self, page=0, size=1000) -> ActualBalance:
        """
        Метод возвращает информацию о балансе, актуальном на текущий день, по кодам товаров без
        остатков и без движения за текущие сутки, для товарных групп «Антисептики и
        дезинфицирующие средства», «Биологически активные добавки к пище», «Молочная
        продукция» и «Упакованная вода».
        5.9. Метод получения актуального баланса на складе
        :param page: Страница
        :param size: Размер страницы
        :return: ActualBalance
        """
        url = f"{self.true_api_v3}/warehouse/balance"
        r = await self.__request(
            "POST",
            url,
            data=json.dumps({"pagination": {"page": page, "perPage": size}}),
            headers={"Content-Type": "application/json"},
        )
        return ActualBalance.model_validate_json(r)

    async def get_gtin_group(self, gtins: list) -> ProductRouteGtinResponse:
        url = f"{self.true_api_v3}/product/route/gtin"
        headers = {"Content-Type": "application/json", "accept": "application/json"}
        return TypeAdapter(ProductRouteGtinResponse).validate_python(
            await self.__request(
                "POST", url, headers=headers, data=json.dumps({"data": gtins})
            )
        )

    async def get_mods(self) -> MODS:
        """
        3.4. Метод получения списка МОД по участнику оборота товаров
        """
        url = f"{self.true_api_v3}/mods/list"
        # url = f'https://markirovka.crpt.ru/bff-elk/v1/manufacture/search?productGroupId=15'
        headers = {"Content-Type": "application/json", "accept": "application/json"}
        return TypeAdapter(MODS).validate_python(
            await self.__request("GET", url, headers=headers)
        )

    async def get_cises_info(self, cises: list[str]) -> list[CisesInfoResponse]:
        url = f"{self.true_api_v3}/cises/info"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        r = await self.__request("POST", url, data=json.dumps(cises), headers=headers)
        return TypeAdapter(list[CisesInfoResponse]).validate_python(r)

    async def product_info(self, gtins: list) -> GisMtProductInfo:
        url = f"{self.true_api_v4}/product/info"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        r = await self.__request(
            "POST", url, data=json.dumps({"gtins": gtins}), headers=headers
        )
        return TypeAdapter(GisMtProductInfo).validate_python(r)

    async def product_info2(self, gtins: list) -> ProductInfoResponse:
        url = f"{self.true_api_v4}/product/info"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        r = await self.__request(
            "POST", url, data=json.dumps({"gtins": gtins}), headers=headers
        )
        return TypeAdapter(ProductInfoResponse).validate_python(r)

    async def get_volume_balances_by_group_name(
            self, groups: List[GroupIds]
    ) -> list[tuple[list[tuple[Product, Balance]], GroupIds]]:
        page = 0
        result = []
        balances = []
        while True:
            actual_balance = await self.get_actual_balance(page=page)
            if config.develope_mode:
                bot_log.debug(actual_balance)
            products_info = await self.product_info(
                await actual_balance.get_all_gtins()
            )
            for pos in actual_balance.balances:
                pi = await products_info.product_by_gtin(pos.gtin)
                if pi is not None:
                    balances.append((pi, pos))
            if len(actual_balance.balances) != 1000:
                break
            page += 1
        for group in groups:
            result.append(
                (
                    [
                        (pi, pos)
                        for pi, pos in balances
                        for piGroupid in pi.productGroupId
                        if piGroupid == group
                    ],
                    group,
                )
            )
        return result

    async def get_ostatki_files(
            self, path_to_save: Path, tovar_groups: list
    ) -> list[OstatkiExcel]:
        if config.develope_mode:
            bot_log.debug(f"pg_groups {tovar_groups}")
        volume_groups = [
            tg for tg in tovar_groups if (await get_pg_info(tg)).is_volume_balance
        ]
        marks_groups = [
            tg for tg in tovar_groups if not (await get_pg_info(tg)).is_volume_balance
        ]
        if config.develope_mode:
            bot_log.debug(f"marks {marks_groups}")
        EXCELS = []
        # Экземлярный учёт
        tasks = await self.wait_dispensers(
            await self.send_KI_info_dispensers(marks_groups)
        )
        for task in tasks:
            if config.develope_mode:
                bot_log.debug(f"Задача: {task}")
            dispenser = await self.get_dispenser_results(
                pg=task.productGroupCode,
                task_ids=task.id,
            )
            csv_path = await self.get_dispenser_file(
                dispenser.list[0].id, path_to_save / task.id
            )
            csv = parse_ostatki_csv(csv_path[0])
            pg = await get_pg_info(task.productGroupCode.name)
            EXCELS.append(OstatkiExcel(**csv.model_dump(), pg_name=pg.name))
        # Объемно-сортовой учёт
        if len(volume_groups) > 0:
            for groups in await self.get_volume_balances_by_group_name(volume_groups):
                EXCELS.append(await write_volume_balance(groups, path_to_save))
        return EXCELS

    async def get_info_gisMt_doc(self, doc_id: str) -> list[DocInfo]:
        url = f"{self.true_api_v4}/doc/{doc_id}/info"
        return TypeAdapter(list[DocInfo]).validate_python(
            await self.__request("GET", url)
        )

    async def wait_gisMt_response(
            self, doc_id: str, sleep: int = 10
    ) -> [DocInfo, bool]:
        while True:
            try:
                await asyncio.sleep(sleep)
                doc_info = (await self.get_info_gisMt_doc(doc_id))[0]
                if doc_info.wait_response():
                    return doc_info, doc_info.gisMt_error_response()
            except ZnakAPIError as e:
                if "Документ не найден в ГИС МТ" not in str(e):
                    raise ZnakAPIError(str(e))
                await asyncio.sleep(1)

    # endregion

    @classmethod
    async def load_from_redis(cls, rds: RedisConnection):
        """
        Загружает состояние объекта
        """
        objcls = await rds.get_cls(cls.__name__)
        if objcls is None:
            raise TrueApiRedisError("Отсутствует созданный TrueApi объект")
        new_cls = cls(**objcls)
        if (
                (new_cls._end_date_token is None)
                or (datetime.now() > datetime.fromtimestamp(new_cls._end_date_token))
                or (new_cls.token is None)
        ):
            await new_cls.create_token()
        return new_cls

    async def save_to_redis(self, rds: RedisConnection) -> None:
        await rds.set_cls(self.__class__.__name__, self.__dict__)

    # endregion
    @property
    def get_end_date_token(self) -> float | None:
        return self._end_date_token


async def main2():
    znak = TrueApi(thumbprint="b2b0777bb77afba0db215b0488bff23b88d8f8f5")
    return await znak.get_ostatki_files("/opt/test", ["tobacco", "beer"])


async def main3(uuid: str):
    znak = TrueApi(thumbprint="DE1927D4B77FAC84E7152566639BA82096CE7156")
    print(znak.get_info_gisMt_doc(uuid))
    # pprint(znak.all_actual_balances_by_group_name(groups))


async def try_auth_mihail_cert(tb, inn_to_auth):
    znak = TrueApi(thumbprint=tb, inn_to_auth=inn_to_auth)
    print(znak.profile_info())


async def check_cises(cises: list, token: str) -> CodeResponse:
    url = f"https://markirovka.crpt.ru/api/v4/true-api/codes/check"
    data = json.dumps({"codes": cises})
    headers = {
        "X-API-KEY": token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    log_request("POST", url=url, headers=headers, data=data)
    response = requests.post(url, headers=headers, data=data)
    log_response(response)
    return CodeResponse.model_validate_json(response.text)


async def test():
    t = TrueApi(inn_to_auth="1642005220")
    await t.create_token()
    profile_info = await t.get_user_info()
    print(profile_info)


if __name__ == "__main__":
    # asyncio.run(test())
    a = {
        "participant_inn": "111111111",
        "producer_inn": "111111111",
        "owner_inn": "111111111",
        "production_date": "2025-03-06",
        "production_type": "OWN_PRODUCTION",
        "products": [
            {
                "uit_code": "0104640334713342215R/Nkf 91FFD0 92dGVzdArvdb0KMP9nkgwLakUpV5hJDAOUJxe3gWrr8GE="
            }
        ]
    }
    print(b64encode(json.dumps(a).encode()).decode())
