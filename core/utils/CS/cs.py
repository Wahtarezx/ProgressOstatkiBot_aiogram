import asyncio
import json
from typing import Union

import aiohttp
from aiohttp import ClientResponse, BasicAuth

import config
from core.loggers.make_loggers import cs_log
from core.utils.CS.pd_model import Client, CardBalance, CardInfo
from core.utils.CS.pd_onlinecheck import OnlineCheck


async def log_request(
    method: str, url: str, headers: dict = None, data: str = None
) -> None:
    log = cs_log.bind(url=url, headers=headers, data=data)
    log.info(f"{method} {url}")


async def log_response(response: ClientResponse) -> None:
    log = cs_log.bind(status_code=response.status, url=response.url)
    log.info(str(response.url))
    if response.ok:
        log.success(await response.text())
    else:
        log.error(await response.text())


class CS:
    def __init__(self):
        self.cfg = config.cs_cfg
        self.cs_url = self.cfg.cs_url()
        self.acc_url = self.cfg.acc_url()
        self.aif_url = self.cfg.aif_url()
        self.cs_onlinecard_url = self.cfg.cs_onlinecard_url()

    async def _get(
        self,
        url: str,
        params: dict = None,
        headers: dict = None,
        data: str = None,
        auth: BasicAuth = None,
    ) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, params=params, headers=headers, auth=auth
            ) as resp:
                await log_request("GET", str(resp.url), headers=headers, data=data)
                await log_response(resp)
                return await resp.text()

    async def _post(
        self, url: str, params: dict = None, headers: dict = None, data: str = None
    ) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, params=params, headers=headers, data=data
            ) as resp:
                await log_request("POST", str(resp.url), headers=headers, data=data)
                await log_response(resp)
                return await resp.text()

    async def get_clients(self) -> list[Client]:
        url = f"{self.cs_url}/dictionaries/clients"
        return [Client(**client) for client in json.loads(await self._get(url))]

    async def get_client_by_id(self, client_id: str | int) -> Client | None:
        url = f"{self.cs_url}/dictionaries/clients/id/{client_id}"
        resp = await self._get(url)
        if resp:
            return Client.model_validate_json(resp)

    async def get_client_by_params(self, params: dict) -> list[Client]:
        url = f"{self.cs_url}/dictionaries/clients/bypage"
        return [
            Client(**client)
            for client in json.loads(await self._get(url, params=params))["content"]
        ]

    async def create_client(self, client: Client, params: dict = None):
        url = f"{self.cs_url}/dictionaries/clients"
        return await self._post(
            url,
            headers={"Content-Type": "application/json"},
            data=client.model_dump_json(exclude_none=True),
            params=params,
        )

    async def get_card_balance(
        self, card_number: Union[int, str], artix_cs_cashid: str
    ) -> CardBalance | None:
        url = f"{self.acc_url}/cards/{card_number}"
        resp = await self._get(url, auth=BasicAuth(login=artix_cs_cashid))
        if resp:
            return CardBalance.model_validate_json(resp)

    async def create_card(self, card: CardInfo, params: dict = None) -> str:
        url = f"{self.cs_url}/dictionaries/cards"
        return await self._post(
            url,
            headers={"Content-Type": "application/json"},
            data=card.model_dump_json(exclude_none=True),
            params=params,
        )

    async def get_card_by_id(self, card_id: int | str) -> CardInfo | None:
        url = f"{self.cs_url}/dictionaries/cards/id/{card_id}"
        resp = await self._get(url)
        if resp:
            return CardInfo.model_validate_json(resp)

    async def create_onlinecheck(self, onlinecheck: OnlineCheck) -> dict:
        url = f"{self.cs_url}/dictionaries/onlinechecks"
        resp = await self._post(
            url,
            headers={"Content-Type": "application/json"},
            data=onlinecheck.model_dump_json(exclude_none=True),
        )
        return json.loads(resp)

    async def get_client_by_phonenubmer(self, phonenumber: str) -> dict:
        url = f"{self.cs_onlinecard_url}/v1/cards/phonenumber/{phonenumber}"
        return json.loads(await self._get(url, auth=BasicAuth("admin", "admin")))

    async def loaddict(
        self,
        shopcode: str,
        data: list[dict],
        dictionaryid: str = None,
        addressstatusserver: str = None,
    ):
        url = f"{self.aif_url}/loaddict"


async def test():
    cs = CS()
    print(await cs.get_card_by_id(52637514901))


if __name__ == "__main__":
    asyncio.run(test())
