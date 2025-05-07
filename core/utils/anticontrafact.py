import asyncio
import os.path
import ssl
import funcy
from pprint import pprint
from collections import namedtuple

import requests
from aiogram.client.session import aiohttp

import config


class Anticontrafact:
    def __init__(self):
        self.url = "https://mobapi.fsrar.ru/api3"

    async def get_excise_info(self, amarks: list):
        certificate_path = os.path.join(
            config.dir_path, "core", "utils", "anticontrafact_client.pem"
        )
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        ssl_context.load_cert_chain(certificate_path)
        tasks = []
        async with aiohttp.ClientSession() as session:
            for a in amarks:
                tasks.append(
                    asyncio.create_task(
                        session.get(f"{self.url}/marklong?pdf417={a}", ssl=ssl_context)
                    )
                )
            responses = await asyncio.gather(*tasks)
            return [
                [
                    f"{(await r.json())['mark']['name']} {(await r.json())['mark']['volume']}л",
                    a,
                ]
                for r in responses
            ]

    async def new_bottles_tuple(self, amarks):
        bottles = namedtuple("bottle", "name count")
        marks_info = await self.get_excise_info(amarks)
        bottles_dict = [{name: amark} for name, amark in marks_info]
        return [
            bottles(name, count)
            for name, count in funcy.merge_with(len, *bottles_dict).items()
        ]


async def main():
    with open("123.txt", "r") as file:
        a = Anticontrafact()
        result = await a.new_bottles_tuple(file.readlines())
    pprint(result)


if __name__ == "__main__":
    print(
        requests.get(
            f"https://mobile.api.crpt.ru/mobile/check?code=4600433602237&codeType=ean13"
        ).json()
    )
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
