from pathlib import Path

from aiogram.client.session import aiohttp
from pydantic import TypeAdapter

import config
from core.loggers.make_loggers import crypto_log
from core.utils.cryptopro.schemas import CertInfo


class CryproProAPIError(Exception):
    pass


class CryproProAPI:
    def __init__(self):
        self.url = config.crypto_cfg.get_url()
        self.thumbprint = config.crypto_cfg.MAIN_THUMBPRINT

    @staticmethod
    async def __request(
        method: str,
        url: str,
        params: dict = None,
        headers: dict = None,
        data: dict = None,
    ):
        crypto_log.bind(url=url, headers=headers, data=data).info(f"{method} {url}")
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, url, params=params, headers=headers, data=data
            ) as resp:
                log = crypto_log.bind(status_code=resp.status, url=resp.url)
                if resp.ok:
                    log.success(await resp.text())
                    return await resp.json()
                else:
                    log.error(await resp.text())
                    raise CryproProAPIError(await resp.text())

    async def get_certificates(self) -> list[CertInfo]:
        url = f"{self.url}/cert/list"
        return TypeAdapter(list[CertInfo]).validate_python(
            await self.__request("GET", url)
        )

    async def get_certificate_info(self, thumbprint: str = None) -> CertInfo:
        if thumbprint is None:
            thumbprint = self.thumbprint
        url = f"{self.url}/cert/{thumbprint}/info"
        return TypeAdapter(CertInfo).validate_python(await self.__request("GET", url))

    async def sign_attach_data(self, data: str) -> str:
        url = f"{self.url}/sign/data"
        return await self.__request("POST", url, params={"data": data})

    async def sign_detach_file(
        self, file_path: Path | str, content: str | bytes
    ) -> str:
        if isinstance(file_path, str):
            file_path = Path(file_path)

        if isinstance(content, str):
            with open(file_path, "wb") as file:
                if content.startswith("%PDF"):
                    file.write(content.encode("utf-8"))
                else:
                    file.write(content.encode("windows-1251"))
        elif isinstance(content, bytes):
            with open(file_path, "wb") as file:
                file.write(content)

        url = f"{self.url}/sign/document"
        return await self.__request(
            "POST", url, data={"document": file_path.read_bytes()}
        )


cryptoPro = CryproProAPI()

if __name__ == "__main__":
    import asyncio

    print(asyncio.run(CryproProAPI().get_certificate_info(config.main_thumbprint)))
