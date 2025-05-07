from core.services.edo.schemas.login.models import EnumEdoProvider
from core.services.markirovka.trueapi import TrueApi
from core.utils.edo_providers.base_model import EdoProvider
from core.utils.edo_providers.edo_lite.model import EdoLite
from core.utils.redis import RedisConnection


class EDOFactoryValueError(Exception):
    pass


class EDOFactory:

    def __init__(self, rds: RedisConnection):
        self.rds = rds
        self.enum_edoprovider: EnumEdoProvider = None

    async def create_edo_operator(self, edoprovider: EnumEdoProvider) -> EdoProvider:
        """Фабрика для создания операторов. Возвращает экземпляр EDOOperator."""
        if edoprovider == EnumEdoProvider.edolite:
            trueapi = await TrueApi.load_from_redis(self.rds)
            provider = EdoLite(
                inn_to_auth=trueapi.inn_to_auth,
                token=trueapi.token,
                _end_date_token=trueapi.get_end_date_token,
            )
            await self.rds.set(last_edoprovider_id=EnumEdoProvider.edolite.value)
        else:
            raise ValueError(f"Неизвестный оператор: {edoprovider}")

        await provider.save_to_redis(self.rds)
        self.enum_edoprovider = edoprovider
        return provider

    async def get_last_edo_operator(self) -> EdoProvider:
        data = await self.rds.get_data()
        last_edoprovider_id = data.get("last_edoprovider_id")
        if last_edoprovider_id is None:
            raise EDOFactoryValueError("Отсутствует последнее подключение к ЭДО")
        return await self.create_edo_operator(EnumEdoProvider(last_edoprovider_id))
