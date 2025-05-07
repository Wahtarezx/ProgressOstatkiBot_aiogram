# -*- coding: utf-8 -*-
import asyncio
import json
import os
import re
import xml
import xml.etree.ElementTree as ET
from collections import namedtuple
from datetime import datetime, timedelta
from random import randint

import httpx
import requests
from aiogram.client.session import aiohttp
from aiohttp import ClientResponse
from bs4 import BeautifulSoup
from loguru import logger

import config
from core.loggers.make_loggers import egais_log
from core.utils import CURL


async def log_request(
    method: str, url: str, headers: dict = None, data: str = None
) -> None:
    log = egais_log.bind(url=url, headers=headers, data=data)
    log.info(f"{method} {url}")


async def log_response(response: ClientResponse) -> None:
    log = egais_log.bind(status_code=response.status, url=response.url)
    log.info(str(response.url))
    if response.ok:
        log.success(await response.text())
    else:
        log.error(await response.text())

class UTMServerError(Exception):
    pass

class UTM:
    def __init__(self, port, ip="localhost"):
        self.port = port
        self.ip = ip
        self.utm_url = f"http://{self.ip}:{self.port}"

    async def _get(
        self, url: str, params: dict = None, headers: dict = None, data: str = None
    ) -> ClientResponse:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as resp:
                await log_request("GET", str(resp.url), headers=headers, data=data)
                await log_response(resp)
                return resp

    async def _post(
        self, url: str, params: dict = None, headers: dict = None, data: str = None
    ) -> ClientResponse:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, params=params, headers=headers, data=data
            ) as resp:
                await log_request("POST", str(resp.url), headers=headers, data=data)
                await log_response(resp)
                return resp

    async def _delete(
        self,
        url: str,
        params: dict = None,
        headers: dict = None,
        data: str = None,
    ) -> ClientResponse:
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                url, params=params, headers=headers, data=data
            ) as resp:
                await log_request("DELETE", str(resp.url), headers=headers, data=data)
                await log_response(resp)
                return resp

    # Возвращает в dict (status, message)
    def parse_ticket_result(self, ticket):
        Response = namedtuple("Response", "doctype status message")
        ticket = requests.get(ticket).text
        tree = ET.fromstring(ticket)
        try:
            doctype = tree.find("*/*/{http://fsrar.ru/WEGAIS/Ticket}DocType").text
            status = tree.find(
                "*/*/*/{http://fsrar.ru/WEGAIS/Ticket}OperationResult"
            ).text
            message = tree.find(
                "*/*/*/{http://fsrar.ru/WEGAIS/Ticket}OperationComment"
            ).text.strip()
        except:
            doctype = tree.find("*/*/{http://fsrar.ru/WEGAIS/Ticket}DocType").text
            status = tree.find("*/*/*/{http://fsrar.ru/WEGAIS/Ticket}Conclusion").text
            message = tree.find(
                "*/*/*/{http://fsrar.ru/WEGAIS/Ticket}Comments"
            ).text.strip()
        return Response(doctype, status, message)

    async def clear_utm(self):
        async with httpx.AsyncClient() as client:
            tickets = await client.get(
                f"{self.utm_url}/opt/out?docType=Ticket", timeout=30.0
            )
            ReplyRestBCode = await client.get(
                f"{self.utm_url}/opt/out?docType=ReplyRestBCode", timeout=30.0
            )
            documents_in = await client.get(
                f"{self.utm_url}/opt/in/state", timeout=30.0
            )

            # Tickets
            # Удаляю Тикет если он старше 45 дней или если Тикет старше 3 дней и со статусом Rejected
            for url in BeautifulSoup(tickets.text, "xml").findAll("url"):
                url_time = datetime.fromisoformat(url.get("timestamp")[:-5])
                if url_time + timedelta(days=45) < datetime.now():
                    await client.delete(url.text)
                elif url_time + timedelta(days=3) < datetime.now():
                    ticket = self.parse_ticket_result(url.text)
                    if ticket.status == "Rejected":
                        await client.delete(url.text)

            # Удаляю ReplyRestBCode если он старше 30 дней
            for url in BeautifulSoup(ReplyRestBCode.text, "xml").findAll("url"):
                url_time = datetime.fromisoformat(url.get("timestamp")[:-5])
                if url_time + timedelta(days=30) < datetime.now():
                    await client.delete(url.text)

            # Удаляю документы из исходящих, если он имеет статус 18 или 10
            for url in BeautifulSoup(documents_in.text, "xml").findAll("url"):
                if url.get("state") == "18" or url.get("state") == "10":
                    await client.delete(f'{self.utm_url}/opt/in/{url.get("replyId")}')

    async def delete_document(self, url):
        async with httpx.AsyncClient() as client:
            await client.delete(url)

    async def wait_answer(self, replyId, timeout=15):
        max_time = 1500
        while max_time > 0:
            print("-- Ожидание ответа от: {}".format(replyId))
            async with httpx.AsyncClient() as client:
                answer = await client.get(
                    f"{self.utm_url}/opt/out?replyId={replyId}", timeout=30.0
                )
                url = BeautifulSoup(answer.text, "xml").findAll("url")
            if len(url) > 1:
                return url
            max_time -= timeout
            await asyncio.sleep(timeout)

    async def get_all_opt_URLS_text(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.utm_url}/opt/out", timeout=30.0)
            return [
                url.text for url in BeautifulSoup(response.text, "xml").findAll("url")
            ]

    async def get_all_opt_URLS_text_by_docType(
        self, docType, maximum_document_age_by_minutes=None
    ):
        result = []
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.utm_url}/opt/out?docType={docType}", timeout=30.0
            )
            if maximum_document_age_by_minutes:
                for url in BeautifulSoup(response.text, "xml").findAll("url"):
                    url_time = datetime.fromisoformat(url.get("timestamp")[:-5])
                    if url_time > datetime.now() - timedelta(
                        minutes=maximum_document_age_by_minutes
                    ):
                        result.append(url.text)
            else:
                result = [
                    url.text
                    for url in BeautifulSoup(response.text, "xml").findAll("url")
                ]
            return result

    async def get_Waybill_and_FORM2REGINFO(self) -> list:
        """Возвращает namedtuple('TTNS', 'id_f2r id_wb ttn_egais shipper_name shipper_inn date wbnumber')"""
        TTNS = namedtuple(
            "TTNS", "id_f2r id_wb ttn_egais shipper_name shipper_inn date wbnumber"
        )
        urls_form = await self.get_all_opt_URLS_text_by_docType("FORM2REGINFO")
        urls_wb = await self.get_all_opt_URLS_text_by_docType("WayBill_v4")
        if len(urls_form) == 0 and len(urls_wb) == 0:
            print("\033[31m{}\033[0m".format("Нету накладных"))
            logger.debug("Не найдено не WayBill не FORM2REGINFO")
            return []
        if len(urls_form) == 0:
            print("\033[31m{}\033[0m".format("Нету FORM2REGINFO"))
            logger.debug("Нету FORM2REGINFO")
            return []
        if len(urls_wb) == 0:
            print("\033[31m{}\033[0m".format("Нету Waybill_v4"))
            logger.error("Нету Waybill_v4")
            return []
        ttns = []
        for url_form in urls_form:
            async with httpx.AsyncClient() as client:
                req = await client.get(url_form, timeout=30.0)
                req = req.text
                if not req.startswith("<"):
                    continue
            TTN = (
                ET.fromstring(req)
                .find("*/*/*/{http://fsrar.ru/WEGAIS/TTNInformF2Reg}WBRegId")
                .text
            )
            WBNUMBER = (
                ET.fromstring(req)
                .find("*/*/*/{http://fsrar.ru/WEGAIS/TTNInformF2Reg}WBNUMBER")
                .text
            )
            SHIPPER_NAME = (
                ET.fromstring(req)
                .find(
                    "*/*/*/{http://fsrar.ru/WEGAIS/TTNInformF2Reg}Shipper/*/{http://fsrar.ru/WEGAIS/ClientRef_v2}ShortName"
                )
                .text
            )
            SHIPPER_INN = (
                ET.fromstring(req)
                .find(
                    "*/*/*/{http://fsrar.ru/WEGAIS/TTNInformF2Reg}Shipper/*/{http://fsrar.ru/WEGAIS/ClientRef_v2}INN"
                )
                .text
            )
            # if "саман" in SHIPPER_NAME.lower():
            #     continue
            date = (
                ET.fromstring(req)
                .find("*/*/*/{http://fsrar.ru/WEGAIS/TTNInformF2Reg}WBDate")
                .text
            )
            for url_wb in urls_wb:
                async with httpx.AsyncClient() as client:
                    req = await client.get(url_wb, timeout=30.0)
                    req = req.text
                    if not req.startswith("<"):
                        continue
                NUMBER = (
                    ET.fromstring(req)
                    .find("*/*/*/{http://fsrar.ru/WEGAIS/TTNSingle_v4}NUMBER")
                    .text
                )
                if NUMBER == WBNUMBER:
                    ttns.append(
                        TTNS(
                            url_form.split("/")[-1],
                            url_wb.split("/")[-1],
                            TTN,
                            SHIPPER_NAME,
                            SHIPPER_INN,
                            date,
                            NUMBER,
                        )
                    )
        return ttns

    async def send_QueryResendDoc(self, fsrar: str, ttn: str):
        files = {"xml_file": CURL.QueryResendDoc(fsrar, ttn)}
        response = requests.post(
            "{}/opt/in/QueryResendDoc".format(self.utm_url), files=files
        )
        if response.status_code == 200:
            request_id = BeautifulSoup(response.text, "xml").find("url").text
            logger.info(f"QueryResendDoc отправлен  request_id: {request_id}")
            return request_id
        else:
            logger.error("QueryResendDoc не отправлен")
            logger.error(f"HTTP code {str(response.status_code)} != 200")
            return False

    async def send_QueryRestBCode(self, FB: str):
        files = {"xml_file": CURL.QueryRestBCode(await self.get_fsrar(), FB)}
        response = requests.post(f"{self.utm_url}/opt/in/QueryRestBCode", files=files)
        if response.status_code == 200:
            request_id = BeautifulSoup(response.text, "xml").find("url").text
            logger.info(f"QueryFormB отправлен  request_id: {request_id}")
            return request_id
        else:
            logger.error("QueryFormB не отправлен")
            logger.error(f"HTTP code {str(response.status_code)} != 200")
            return False

    async def send_QueryRests_v2(self):
        files = {"xml_file": CURL.QueryRests_v2(await self.get_fsrar())}
        response = requests.post(f"{self.utm_url}/opt/in/QueryRests_v2", files=files)
        if response.status_code == 200:
            request_id = BeautifulSoup(response.text, "xml").find("url").text
            print(
                "\033[32m{}, request_id: {}\033[0m".format(
                    "QueryRests_v2 отправлен", request_id
                )
            )
            return request_id
        else:
            print("\033[31m{}\033[0m".format("QueryRests_v2 не отправлен"))
            print(
                "\033[31m{}\033[0m".format(
                    "HTTP code != 200 --- "
                    + "status code = "
                    + str(response.status_code)
                )
            )
            raise ConnectionError("Что-то пошло не так, запрос не принят")

    async def send_QueryRestsShop_V2(self):
        files = {"xml_file": CURL.QueryRestsShop_V2(await self.get_fsrar())}
        response = requests.post(
            f"{self.utm_url}/opt/in/QueryRestsShop_V2", files=files
        )
        if response.status_code == 200:
            request_id = BeautifulSoup(response.text, "xml").find("url").text
            print(
                "\033[32m{}, request_id: {}\033[0m".format(
                    "QueryRestsShop_V2 отправлен", request_id
                )
            )
            return request_id
        else:
            print("\033[31m{}\033[0m".format("QueryRestsShop_V2 не отправлен"))
            print(
                "\033[31m{}\033[0m".format(
                    "HTTP code != 200 --- "
                    + "status code = "
                    + str(response.status_code)
                )
            )
            raise ConnectionError(
                "Что-то пошло не так, запрос QueryRestsShop_V2 не принят"
            )

    async def send_ActWriteOff_v3(self, QueryRests_v2_xml_string):
        if QueryRests_v2_xml_string:
            result = []
            products = ET.fromstring(QueryRests_v2_xml_string).findall(
                "*/*/*/{http://fsrar.ru/WEGAIS/ReplyRests_v2}StockPosition"
            )
            for identity, product in enumerate(products, 1):
                body = """                <awr:Position>
                    <awr:Identity>{}</awr:Identity>
                    <awr:Quantity>{}</awr:Quantity>
                    <awr:InformF1F2>
                        <awr:InformF2>
                            <pref:F2RegId>{}</pref:F2RegId>
                        </awr:InformF2>
                    </awr:InformF1F2>
                </awr:Position>\n""".format(
                    str(identity),
                    product.find("{http://fsrar.ru/WEGAIS/ReplyRests_v2}Quantity").text,
                    product.find(
                        "{http://fsrar.ru/WEGAIS/ReplyRests_v2}InformF2RegId"
                    ).text,
                )
                result.append(body)

            files = {"xml_file": CURL.ActWriteOff_v3(await self.get_fsrar(), result)}
            response = requests.post(
                f"{self.utm_url}/opt/in/ActWriteOff_v3", files=files
            )
            if response.status_code == 200:
                request_id = BeautifulSoup(response.text, "xml").find("url").text
                print(
                    "\033[32m{}, request_id: {}\033[0m".format(
                        "ActWriteOff_v3 отправлен", request_id
                    )
                )
                return request_id
            else:
                print("\033[31m{}\033[0m".format("ActWriteOff_v3 не отправлен"))
                print(
                    "\033[31m{}\033[0m".format(
                        "HTTP code != 200 --- "
                        + "status code = "
                        + str(response.status_code)
                    )
                )
                raise ConnectionError(
                    "Что-то пошло не так, запрос ActWriteOff_v3 не принят"
                )
        else:
            print("\033[31m{}\033[0m".format("QueryRests_v2_xml_string not True"))
            raise ConnectionError("Что-то пошло не так. Запрос QueryRests_v2 не принят")

    async def send_ActWriteOffShop_v2(self, QueryRestsShop_V2_xml_string):
        if QueryRestsShop_V2_xml_string:
            result = []
            tree = ET.fromstring(QueryRestsShop_V2_xml_string)
            for count, el in enumerate(
                tree.findall(
                    ".//{http://fsrar.ru/WEGAIS/ReplyRestsShop_v2}ShopPosition"
                ),
                1,
            ):
                try:
                    Quantity = el.find(
                        "{http://fsrar.ru/WEGAIS/ReplyRestsShop_v2}Quantity"
                    ).text
                    FullName = el.find(
                        ".//{http://fsrar.ru/WEGAIS/ProductRef_v2}FullName"
                    ).text
                    AlcCode = el.find(
                        ".//{http://fsrar.ru/WEGAIS/ProductRef_v2}AlcCode"
                    ).text
                    Capacity = el.find(
                        ".//{http://fsrar.ru/WEGAIS/ProductRef_v2}Capacity"
                    ).text
                    UnitType = el.find(
                        ".//{http://fsrar.ru/WEGAIS/ProductRef_v2}UnitType"
                    ).text
                    AlcVolume = el.find(
                        ".//{http://fsrar.ru/WEGAIS/ProductRef_v2}AlcVolume"
                    ).text
                    ProductVCode = el.find(
                        ".//{http://fsrar.ru/WEGAIS/ProductRef_v2}ProductVCode"
                    ).text
                    ClientRegId = el.find(
                        ".//{http://fsrar.ru/WEGAIS/ClientRef_v2}ClientRegId"
                    ).text
                    INN = el.find(".//{http://fsrar.ru/WEGAIS/ClientRef_v2}INN").text
                    KPP = el.find(".//{http://fsrar.ru/WEGAIS/ClientRef_v2}KPP").text
                    FullName_UL = el.find(
                        ".//{http://fsrar.ru/WEGAIS/ClientRef_v2}FullName"
                    ).text
                    ShortName = el.find(
                        ".//{http://fsrar.ru/WEGAIS/ClientRef_v2}ShortName"
                    ).text
                    Country = el.find(
                        ".//{http://fsrar.ru/WEGAIS/ClientRef_v2}Country"
                    ).text
                    RegionCode = el.find(
                        ".//{http://fsrar.ru/WEGAIS/ClientRef_v2}RegionCode"
                    ).text
                    description = el.find(
                        ".//{http://fsrar.ru/WEGAIS/ClientRef_v2}description"
                    ).text

                    position = """
                            <awr:Position>
                      <awr:Identity>{0}</awr:Identity>
                      <awr:Quantity>{1}</awr:Quantity>
                      <awr:Product>
                        <pref:FullName>{2}</pref:FullName>
                        <pref:AlcCode>{3}</pref:AlcCode>
                        <pref:Capacity>{4}</pref:Capacity>
                        <pref:UnitType>{5}</pref:UnitType>
                        <pref:AlcVolume>{6}</pref:AlcVolume>
                        <pref:ProductVCode>{7}</pref:ProductVCode>
                        <pref:Producer>
                          <oref:UL>
                            <oref:ClientRegId>{8}</oref:ClientRegId>
                            <oref:FullName>{9}"</oref:FullName>
                            <oref:ShortName>{10}</oref:ShortName>
                            <oref:INN>{11}</oref:INN>
                            <oref:KPP>{12}</oref:KPP>
                            <oref:address>
                              <oref:Country>{13}</oref:Country>
                              <oref:RegionCode>{14}</oref:RegionCode>
                              <oref:description>{15}</oref:description>
                            </oref:address>
                          </oref:UL>
                        </pref:Producer>
                      </awr:Product>
                    </awr:Position>
                    """.format(
                        count,
                        Quantity,
                        FullName,
                        AlcCode,
                        Capacity,
                        UnitType,
                        AlcVolume,
                        ProductVCode,
                        ClientRegId,
                        INN,
                        KPP,
                        FullName_UL,
                        ShortName,
                        Country,
                        RegionCode,
                        description,
                    )
                    result.append(position)
                except Exception as e:
                    print(e)
            with open("test.xml", "w", encoding="utf-8") as f:
                f.write(CURL.ActWriteOffShop_v2(await self.get_fsrar(), result))
                """
                ТЕСТЫ СПИСАНИЯ
                """
        #     files = {
        #         'xml_file': CURL.ActWriteOffShop_v2(await self.get_fsrar(), result)
        #     }
        #     response = requests.post(f'{self.utm_url}/opt/in/ActWriteOffShop_v2', files=files)
        #     if response.status_code == 200:
        #         request_id = BeautifulSoup(response.text, "xml").find("url").text
        #         print("\033[32m{}, request_id: {}\033[0m".format("ActWriteOffShop_v2 отправлен", request_id))
        #         return request_id
        #     else:
        #         print("\033[31m{}\033[0m".format("ActWriteOffShop_v2 не отправлен"))
        #         print("\033[31m{}\033[0m".format("HTTP code != 200 --- " + "status code = " + str(response.status_code)))
        #         exit(1)
        # else:
        #     print("\033[31m{}\033[0m".format("QueryRests_v2_xml_string not True"))
        #     exit(1)

    async def send_WayBillv4(self, TTN):
        """
        Отправляет акт приёма ТТН
        Принимает только одну накладную
        TTN = только цифры
        """
        for i in range(3):
            files = {"xml_file": CURL.WayBillAct_v4(TTN, await self.get_fsrar())}
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.utm_url}/opt/in/WayBillAct_v4", files=files, timeout=30.0
                )
                try:
                    if str(response.status_code).startswith('5'):
                        raise UTMServerError(f'Код ошибки: {response.status_code}')
                    return response
                except UTMServerError:
                    pass
        return response

    def check_utm_error(self):
        try:
            status_UTM = requests.get(self.utm_url, timeout=2).ok
        except Exception as ex:
            print("\033[31m{}\033[0m".format(ex))
            status_UTM = False
        return status_UTM

    async def check_beer_waybill(self, url_WB, port):
        async with httpx.AsyncClient() as client:
            response = await client.get(url_WB, timeout=30.0)
            WB = BeautifulSoup(response.text, "xml")
            beer_WB = ET.fromstring(response.text)
        beer = False
        if len(WB.findAll("amc")) == 0:
            beer = True
        elif len(WB.findAll("boxnumber")) == 0:
            beer = True
        elif port == "18082":
            beer = True

        if beer:
            ttn = namedtuple("Bottles", "name quantity")
            Positions = beer_WB.findall(
                "*/*/*/{http://fsrar.ru/WEGAIS/TTNSingle_v4}Position"
            )
            result = []
            for pos in Positions:
                Product = pos.find("{http://fsrar.ru/WEGAIS/TTNSingle_v4}Product")
                FullName = Product.find(
                    "{http://fsrar.ru/WEGAIS/ProductRef_v2}FullName"
                ).text
                Quantity = pos.find(
                    "{http://fsrar.ru/WEGAIS/TTNSingle_v4}Quantity"
                ).text
                result.append(ttn(FullName, Quantity))
            return result
        return beer

    async def send_divirgence_ttn(self, url_WB, url_f2r, boxs, ttn_egais):
        async def get_informr2regid(identity):
            async with httpx.AsyncClient() as client:
                F2R = ET.fromstring((await client.get(url_f2r, timeout=30.0)).text)
            Positions = F2R.findall(
                "*/*/*/{http://fsrar.ru/WEGAIS/TTNInformF2Reg}Position"
            )
            for pos in Positions:
                Identity = pos.find(
                    "{http://fsrar.ru/WEGAIS/TTNInformF2Reg}Identity"
                ).text
                if identity == Identity:
                    InformF2RegId = pos.find(
                        "{http://fsrar.ru/WEGAIS/TTNInformF2Reg}InformF2RegId"
                    ).text
                    return InformF2RegId

        boxes = namedtuple("Boxes", "identity quantity amc informF2RegId")
        boxs_not_scanned = [box.boxnumber for box in boxs if not box.scaned]
        async with httpx.AsyncClient() as client:
            WB = ET.fromstring((await client.get(url_WB, timeout=30.0)).text)

        Positions = WB.findall("*/*/*/{http://fsrar.ru/WEGAIS/TTNSingle_v4}Position")
        result = []
        for pos in Positions:
            amc = []
            Identity = pos.find("{http://fsrar.ru/WEGAIS/TTNSingle_v4}Identity").text
            InformF2RegId = await get_informr2regid(Identity)
            Quantity = pos.find("{http://fsrar.ru/WEGAIS/TTNSingle_v4}Quantity").text
            boxs = pos.findall("*/*/{http://fsrar.ru/WEGAIS/CommonV3}boxpos")
            for box in boxs:
                boxnumber = box.find("{http://fsrar.ru/WEGAIS/CommonV3}boxnumber").text
                if boxnumber in boxs_not_scanned:
                    amcs = box.findall("*/{http://fsrar.ru/WEGAIS/CommonV3}amc")
                    Quantity = int(Quantity) - len(amcs)
                    for a in amcs:
                        amc.append(a.text)
            result.append(boxes(Identity, Quantity, amc, InformF2RegId))
        files = {
            "xml_file": CURL.divirgence_ttn(
                fsrar=await self.get_fsrar(), boxes=result, ttn_egais=ttn_egais
            )
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.utm_url}/opt/in/WayBillAct_v4", files=files, timeout=30.0
            )
        return response

    async def get_box_info_from_Waybill(self, url_WB, autoscan: bool = False):
        """
        Возвращает Box(name, capacity, boxnumber, count_bottles, amarks, scaned)
        """
        boxinfo = namedtuple(
            "Box", "identity name capacity boxnumber count_bottles amarks scaned"
        )
        async with httpx.AsyncClient() as client:
            WB = ET.fromstring((await client.get(url_WB, timeout=30.0)).text)
        Positions = WB.findall("*/*/*/{http://fsrar.ru/WEGAIS/TTNSingle_v4}Position")
        result = []
        for pos in Positions:
            identity = pos.find("{http://fsrar.ru/WEGAIS/TTNSingle_v4}Identity").text
            Product = pos.find("{http://fsrar.ru/WEGAIS/TTNSingle_v4}Product")
            FullName = Product.find(
                "{http://fsrar.ru/WEGAIS/ProductRef_v2}FullName"
            ).text
            ShortName = Product.find("{http://fsrar.ru/WEGAIS/ProductRef_v2}ShortName")
            ShortName = ShortName.text if ShortName is not None else False
            Capacity = Product.find(
                "{http://fsrar.ru/WEGAIS/ProductRef_v2}Capacity"
            ).text
            boxs = pos.findall("*/*/{http://fsrar.ru/WEGAIS/CommonV3}boxpos")
            for box in boxs:
                boxnumber = box.find("{http://fsrar.ru/WEGAIS/CommonV3}boxnumber")
                if boxnumber is not None:
                    boxnumber = boxnumber.text
                else:
                    boxnumber = "".join([str(randint(0, 9)) for i in range(26)])
                    logger.debug(
                        f'Не найдена коробка в позиции "{identity}" и присвоил ей случайное число "{boxnumber}"'
                    )
                # Если нужны только уникальные коробки
                # if boxnumber not in [b.boxnumber for b in result]:
                amarks = [
                    box.text
                    for box in box.findall("*/{http://fsrar.ru/WEGAIS/CommonV3}amc")
                ]
                count_bottles_in_box = len(amarks)
                scan = True if autoscan else False
                if ShortName:
                    result.append(
                        boxinfo(
                            identity,
                            ShortName,
                            Capacity,
                            boxnumber,
                            count_bottles_in_box,
                            amarks,
                            scan,
                        )
                    )
                else:
                    result.append(
                        boxinfo(
                            identity,
                            FullName,
                            Capacity,
                            boxnumber,
                            count_bottles_in_box,
                            amarks,
                            scan,
                        )
                    )
        return result

    async def get_accepted_ttn(self):
        return await self.get_tickets_by_status(["подтверждена"])

    async def get_tickets_by_status(self, statuses):
        """
        :param statuses: list('...', ..)
        :return: Отдаёт принятые ТТНки списком [[ttnNumber, ...]]
        """
        tickets = await self.get_all_opt_URLS_text_by_docType("Ticket")
        result = []
        tasks = []
        async with aiohttp.ClientSession() as session:
            for ttn in tickets:
                tasks.append(asyncio.create_task(session.get(ttn)))
            responses = await asyncio.gather(*tasks)
            for res in responses:
                text = await res.text()
                for status in statuses:
                    if status in text:
                        ttn = re.findall("TTN-[0-9]+", text)[0]
                        result.append(re.findall("[0-9]+", ttn)[0])
        return result

    async def get_rejected_or_withdrawn_ttn(self):
        """
        Отдаёт отозванные или отказанные ТТНки списком [[ttnNumber, ...]]
        """
        tickets = await self.get_all_opt_URLS_text_by_docType("Ticket")
        result = []
        tasks = []
        async with aiohttp.ClientSession() as session:
            for ttn in tickets:
                tasks.append(asyncio.create_task(session.get(ttn)))
            responses = await asyncio.gather(*tasks)
            for res in responses:
                text = await res.text()
                if re.findall("отозвана|отказана", text):
                    ttn = re.findall("TTN-[0-9]+", text)[0]
                    result.append(re.findall("[0-9]+", ttn)[0])
        return result

    async def add_to_whitelist(self, url_WB, boxs, cash) -> None:
        """
        Добавляет в белый список акцизы
        :param url_WB: Полная ссылка на накладную
        :param boxs: Коробки
        :param cash: Только цифры компа
        :return: Пишит amarks.txt для белого списка на сервер
        """
        boxsidentity_not_scanned = (box.identity for box in boxs if not box.scaned)
        amark_txt = os.path.join(
            config.server_path, "whitelist", str(cash), "amark.txt"
        )
        if not os.path.exists(os.path.join(config.server_path, "whitelist", str(cash))):
            os.makedirs(os.path.join(config.server_path, "whitelist", str(cash)))
        async with httpx.AsyncClient() as client:
            request = await client.get(url_WB, timeout=30.0)
            txt = request.text
            try:
                WB = ET.fromstring(txt)
            except xml.etree.ElementTree.ParseError:
                with open(amark_txt, "a+") as file:
                    for box in boxs:
                        for amark in box.amarks:
                            file.write(f"{amark}\n")
                return

        with open(amark_txt, "a+") as file:
            Positions = WB.findall(
                "*/*/*/{http://fsrar.ru/WEGAIS/TTNSingle_v4}Position"
            )
            for pos in Positions:
                EAN = pos.find("{http://fsrar.ru/WEGAIS/TTNSingle_v4}EAN13")
                identity = pos.find("{http://fsrar.ru/WEGAIS/TTNSingle_v4}Identity")
                boxs = pos.findall("*/*/{http://fsrar.ru/WEGAIS/CommonV3}boxpos")
                for box in boxs:
                    if identity not in boxsidentity_not_scanned:
                        amcs = box.findall("*/{http://fsrar.ru/WEGAIS/CommonV3}amc")
                        for a in amcs:
                            if EAN:
                                file.write(f"{a} {EAN.text}\n")
                            else:
                                file.write(f"{a}")

    async def get_ttns_from_ReplyNATTN(self):
        """
        Отдаёт кортеж ТТНнок [TTN(WbRegID ttnNumber ttnDate Shipper),]
        """
        ttn = namedtuple("TTN", "WbRegID ttnNumber ttnDate Shipper")
        result = []
        replynattns = await self.get_all_opt_URLS_text_by_docType("ReplyNATTN", 60 * 24)
        if not replynattns:
            text = (
                "Не нашлось документа с общим списком накладных (ReplyNATTN) за текущий день. "
                "Обратитесь в тех.поддержку или отправьте накладную через ТТН ЕГАИС"
            )
            raise ValueError(text)
        for replydoc in replynattns:
            ReplyNATTN = BeautifulSoup(requests.get(replydoc).text, "xml")
            date_NATTN = ReplyNATTN.find("ReplyDate").text.split("T")[0]
            if datetime.strftime(datetime.now(), "%Y-%m-%d") == date_NATTN:
                TTNs = ReplyNATTN.findAll("NoAnswer")
                if not TTNs:
                    raise ValueError("У вас нет не принятых накладных")
                for index, doc in enumerate(TTNs):
                    WbRegID = doc.find("WbRegID").text
                    if "TTN-00" in WbRegID:
                        logger.debug(
                            f'Скипнул старую накладную из ReplyNATTN "{WbRegID}"'
                        )
                        continue
                    ttnNumber = doc.find("ttnNumber").text
                    ttnDate = doc.find("ttnDate").text
                    Shipper = doc.find("Shipper").text
                    result.append(
                        ttn(
                            WbRegID,
                            ttnNumber,
                            ttnDate,
                            Shipper,
                        )
                    )
            else:
                await self.delete_document(replydoc)
        if result is None:
            text = (
                "Не нашлось документа с общим списком накладных (ReplyNATTN) за текущий день. "
                "Обратитесь в тех.поддержку или отправьте накладную через ТТН ЕГАИС"
            )
            raise ValueError(text)
        return result

    async def not_accepted_ttn(self):
        """
        :return кортеж ТТНнок [TTN(WbRegID ttnNumber ttnDate Shipper),]
        """
        ReplyNATTN = await self.get_ttns_from_ReplyNATTN()
        tickets_accept_or_rejected_or_withdrawn = await self.get_tickets_by_status(
            ["подтверждена", "отозвана", "отказана"]
        )
        return [
            ttn
            for ttn in ReplyNATTN
            if ttn.WbRegID not in tickets_accept_or_rejected_or_withdrawn
        ]

    async def get_date_rutoken(self) -> datetime | None:
        url = f"{self.utm_url}/api/info/list"
        response = await self._get(url)
        date_rutoken = (await response.json())["gost"]["expireDate"].split("+")[0]
        if "error" not in date_rutoken.lower():
            date_rutoken = datetime.strptime(date_rutoken, "%Y-%m-%d %H:%M:%S ")
            return date_rutoken

    async def get_name_rutoken(self):
        name = json.loads(requests.get(f"{self.utm_url}/api/gost/orginfo").text)["cn"]
        return name

    async def get_fsrar(self):
        return (
            BeautifulSoup(requests.get("{}/diagnosis".format(self.utm_url)).text, "xml")
            .find("CN")
            .text
        )

    async def get_cash_info(self) -> dict | None:
        """
        Возвращает JSON формат
        {ID, Owner_ID, Full_Name, Short_Name, INN, KPP, Country_Code, Region_Code, Dejure_Address, Fact_Address, isLicense, Version_ts, pass_owner_id}
        """
        fsrar = await self.get_fsrar()
        # response = json.loads(requests.get("{}/api/rsa/orginfo".format(self.utm_url)).text)
        # if not response.get('o') or response.get('o') == 'O':
        response = json.loads(requests.get("{}/api/rsa".format(self.utm_url)).text).get(
            "rows"
        )
        if response is not None:
            response = [_ for _ in response if _["Owner_ID"] == fsrar][0]
            response["Short_Name"] = (
                response.get("Short_Name")
                .upper()
                .replace("ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ", "ООО")
            )
        # else:
        #     if 'ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ' in response.get('o').upper():
        #         o = response.get('o').upper().replace('ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ', "ООО")
        #     else:
        #         o = response.get('o')
        #     response = {
        #         "Owner_ID": response.get('cn'),
        #         "Full_Name": o,
        #         "Short_Name": o,
        #         "INN": response.get('ou'),
        #         "KPP": response.get('c'),
        #     }
        return response


if __name__ == "__main__":
    utm = UTM(port="8082", ip="10.8.18.166")
    # utm2 = UTM(port="18082", ip="10.8.1.210")
    # a = asyncio.run(utm.get_accepted_ttn())
    # a = asyncio.run(utm.get_date_rutoken())
    # ab = asyncio.run(utm2.get_date_rutoken())
    # print(a)
    # print(datetime.fromisoformat("2023-09-05T16:01:52.310+0300"[:-5]))
    print(asyncio.run(utm.get_date_rutoken()))
