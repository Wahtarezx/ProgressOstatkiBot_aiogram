import json
import ssl
from datetime import timedelta, datetime

from aiogram.client.session import aiohttp
from aiohttp import ClientSession, ClientResponse, BasicAuth
from dateutil import parser

import config
from core.loggers.make_loggers import foreman_log
from core.utils.foreman.pd_model import ForemanCash, print_field_aliases


async def log_request(
    method: str, url: str, headers: dict = None, data: str = None
) -> None:
    log = foreman_log.bind(url=url, headers=headers, data=data)
    log.info(f"{method} {url}")


async def log_response(response: ClientResponse) -> None:
    log = foreman_log.bind(status_code=response.status, url=response.url)
    log.info(str(response.url))
    if response.ok:
        log.success(await response.text())
    else:
        log.error(await response.text())


class Foreman:
    def __init__(self, version_ubuntu=18):
        self.version_ubuntu = version_ubuntu
        if version_ubuntu == 18:
            self.base_url = config.f18_base_url
            self.username = config.f18_username
            self.password = config.f18_password
        else:
            self.base_url = config.f14_base_url
            self.username = config.f14_username
            self.password = config.f14_password
        self.auth = BasicAuth(self.username, self.password)

    async def _request(self, method: str, url, params=None, headers=None, data=None):
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with ClientSession(connector=connector) as session:
            async with session.request(
                method, url, params=params, headers=headers, data=data, auth=self.auth
            ) as resp:
                await log_request(method, url, headers)
                await log_response(resp)
                if resp.ok:
                    return await resp.json()
                raise Exception(f"Ошибка запроса: {resp.status}\n {await resp.text()}")

    async def get_architectures(self):
        """Получить список архитектур."""
        url = f"{self.base_url}/api/architectures"
        return await self._request("GET", url)

    async def get_hosts(self, search: str = "cash-", order: str = "last_report DESC"):
        """Получить список хостов"""
        url = f"{self.base_url}/api/hosts"
        per_page = 99999999999 if self.version_ubuntu == 14 else "all"
        params = {
            "per_page": per_page,
            "search": search,
            "order": order,
        }
        return await self._request("GET", url, params)

    async def get_host_facts(self, host_id: int):
        """Получить факты хоста"""
        url = f"{self.base_url}/api/hosts/{host_id}/facts"
        return await self._request("GET", url, params={"per_page": "10000"})

    async def get_fact_values(self, search: str, order: str = "last_report DESC"):
        """Получить факты хостов"""
        url = f"{self.base_url}/api/fact_values"
        per_page = 99999999999 if self.version_ubuntu == 14 else "all"
        params = {"per_page": per_page, "search": search}
        return await self._request("GET", url, params)


async def get_cash(cash_number: str) -> ForemanCash:
    print('ищу кассу')
    foreman = Foreman(18)
    hosts = await foreman.get_hosts(search=cash_number)
    if hosts["subtotal"] == 0:
        foreman = Foreman(14)
        hosts = await foreman.get_hosts(search=cash_number)
        if hosts["subtotal"] == 0:
            raise ValueError(f'Не удалось найти кассу с номером "{cash_number}"')

    facts = (await foreman.get_host_facts(hosts["results"][0]["id"]))["results"]
    for name, value in facts.items():
        return ForemanCash.model_validate_json(json.dumps(value))


async def get_cashes(search: str, f_versions: list[int] = None) -> list[ForemanCash]:
    if f_versions is None:
        f_versions = [18, 14]

    cashes = []
    cashes_set = set()  # Set для уникальных значений
    for f_ver in f_versions:
        foreman = Foreman(f_ver)

        hosts = await foreman.get_hosts(
            search=search
        )  # Предполагаем, что это асинхронный запрос
        for host in hosts["results"]:
            facts = await foreman.get_host_facts(
                host["id"]
            )  # Асинхронный запрос для фактов
            for name, value in facts["results"].items():
                f_cash = ForemanCash.model_validate_json(json.dumps(value))
                unique_key = (f_cash.shopcode, f_cash.cashcode)
                if unique_key not in cashes_set:
                    cashes_set.add(unique_key)
                    cashes.append(f_cash)

    return cashes


async def get_actual_all_cashes(max_last_report_days: timedelta) -> list[ForemanCash]:
    cashes = []
    cashes_set = set()  # Set для уникальных значений
    for f_ver in [18, 14]:
        foreman = Foreman(f_ver)

        hosts = await foreman.get_hosts()  # Предполагаем, что это асинхронный запрос
        for host in hosts["results"]:
            if host.get("last_report") is None:
                continue
            last_report = parser.isoparse(host["last_report"]).replace(tzinfo=None)
            if datetime.now() - last_report > max_last_report_days:
                continue
            facts = await foreman.get_host_facts(
                host["id"]
            )  # Асинхронный запрос для фактов
            for name, value in facts["results"].items():
                f_cash = ForemanCash.model_validate_json(json.dumps(value))
                unique_key = (f_cash.shopcode, f_cash.cashcode)
                if unique_key not in cashes_set:
                    cashes_set.add(unique_key)
                    cashes.append(f_cash)
    return cashes


async def get_info_from_all_cashes_by_inn(inns: list[str]) -> list[ForemanCash]:
    cashes = []
    for f_ver in [18, 14]:
        foreman = Foreman(f_ver)
        if f_ver == 14:
            search = "artix_inn"
            for cash, facts in (await foreman.get_fact_values(search=search))[
                "results"
            ].items():
                if facts[search] in inns:
                    hosts = await foreman.get_hosts(search=cash)
                    for host in hosts["results"]:
                        facts = (await foreman.get_host_facts(host["id"]))["results"]
                        for name, value in facts.items():
                            cash = ForemanCash.model_validate_json(json.dumps(value))

                            if cash.inn not in inns:
                                break

                            if (
                                (cash.ip() in (f.ip() for f in cashes))
                                or (cash.inn, cash.kpp)
                                in ((f.inn, f.kpp) for f in cashes)
                                or (
                                    cash.kkm1_fn_number
                                    in (f.kkm1_fn_number for f in cashes)
                                )
                            ):
                                break

                            cash.os_name = (
                                "Обновлен"
                                if cash.os_name == "bionic"
                                else "Не обновлен"
                            )
                            cashes.append(cash)
        else:
            search = " ".join([f"facts.artix_inn = {inn} or" for inn in inns]).rstrip(
                " or"
            )
            hosts = await foreman.get_hosts(search=search)
            for host in hosts["results"]:
                facts = (await foreman.get_host_facts(host["id"]))["results"]
                for name, value in facts.items():
                    cash = ForemanCash.model_validate_json(json.dumps(value))

                    if cash.inn not in inns:
                        break

                    if (
                        (cash.ip() in (f.ip() for f in cashes))
                        or (cash.inn, cash.kpp) in ((f.inn, f.kpp) for f in cashes)
                        or (cash.kkm1_fn_number in (f.kkm1_fn_number for f in cashes))
                    ):
                        break
                    cash.os_name = (
                        "Обновлен" if cash.os_name == "bionic" else "Не обновлен"
                    )
                    cashes.append(cash)
    return cashes


async def get_all_info():
    result = []
    for f in [Foreman(18), Foreman(14)]:
        ids = [r["id"] for r in (await f.get_hosts())["results"]]
        for id in ids:
            facts = (await f.get_host_facts(id))["results"]
            for name, value in facts.items():
                result.append(ForemanCash.model_validate_json(json.dumps(value)))
    return result


async def test():
    await get_info_from_all_cashes_by_inn(config.ROSSICH_INNS)


if __name__ == "__main__":
    import asyncio

    # # print(asyncio.run(get_cash('facts.artix_shopname = BioHacking')))
    # dt = pd.DataFrame.from_dict([c.__dict__ for c in asyncio.run(get_info_from_all_cashes_by_inn(config.SAMAN_INNS))])
    # dt.to_excel(
    #     Path(config.dir_path, 'saman.xlsx'),
    #     index=False,
    # )
    asyncio.run(test())
