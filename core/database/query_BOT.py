import json
from collections import namedtuple
from typing import Union, Sequence

from sqlalchemy import select, update, insert, delete
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import *

from core.database.modelBOT import *
from core.database.model_logs import *
from core.database.models_enum import Roles
from core.database.query_PROGRESS import get_cash_info
from core.services.egais.goods.pd_models import _Goods
from core.utils.foreman.pd_model import ForemanCash

engine = create_engine(
    f"mysql+pymysql://{config.db_user}:{config.db_password}@{config.ip}:{config.port}/{config.bot_database}?charset=utf8mb4",
    pool_recycle=3600,
    pool_timeout=30,
)
Base = sqlalchemy.orm.declarative_base()
Session = sessionmaker(bind=engine)


class Database:
    def __init__(self):
        self.engine = create_async_engine(config.db_cfg.get_url())
        self.AsyncSession = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def get_client_info(self, user_id: str) -> Clients | None:
        async with self.AsyncSession() as session:
            q = await session.execute(select(Clients).where(Clients.user_id == user_id))
            return q.scalars().first()

    async def get_client_info_by_phone(self, phone: str) -> Clients | None:
        async with self.AsyncSession() as session:
            q = await session.execute(
                select(Clients).where(Clients.phone_number == phone)
            )
            return q.scalars().first()

    async def get_all_clients(self) -> list[Clients]:
        async with self.AsyncSession() as session:
            q = await session.execute(select(Clients))
            return q.scalars().all()

    async def get_clients_by_shopcodes(self, shopcodes: list[int]) -> list[Clients]:
        async with self.AsyncSession() as session:
            q = await session.execute(
                select(Clients)
                .join(ArtixAutologin, Clients.user_id == ArtixAutologin.user_id)
                .where(ArtixAutologin.shopcode.in_(shopcodes))
            )
            return q.scalars().all()

    async def get_cash_in_acceptlist(self):
        """Отдаёт номера компьютеров которые могут принимать ТТН без сканирования"""
        async with self.AsyncSession() as session:
            q = await session.execute(select(Acceptlist))
            return q.scalars().all()

    async def add_cash_in_acceptlist(
            self,
            cash_number: str,
            inn: str,
            kpp: str,
            accept_all_inn: bool,
            may_accept_inn: list[str] | None,
    ) -> None:
        """Добавляет номер компьютера в список которые могут принимать ТТН без сканирования"""
        async with self.AsyncSession() as session:
            await session.execute(
                insert(Acceptlist).values(
                    cash_number=cash_number,
                    inn=inn,
                    kpp=kpp,
                    accept_all_inn=accept_all_inn,
                    may_accept_inn=json.dumps(may_accept_inn),
                )
            )
            await session.commit()

    async def update_role(self, user_id: str, role: str):
        async with self.AsyncSession() as session:
            q = await session.execute(
                select(ClientRole).where(ClientRole.user_id == user_id)
            )
            client_role = q.scalars().first()
            if client_role is None:
                await session.execute(
                    insert(ClientRole).values(user_id=user_id, role=role)
                )
            else:
                await session.execute(
                    update(ClientRole)
                    .where(ClientRole.user_id == user_id)
                    .values(role=role)
                )
            await session.commit()

    async def delete_cash_from_acceptlist(self, cash_number: str) -> None:
        """Удалить номер компьютера из списка которые могут принимать ТТН без сканирования"""
        async with self.AsyncSession() as session:
            await session.execute(
                delete(Acceptlist).where(Acceptlist.cash_number == cash_number)
            )
            await session.commit()

    async def get_admins(self) -> list[Clients]:
        async with self.AsyncSession() as session:
            q = await session.execute(
                select(Clients)
                .join(ClientRole)
                .where(ClientRole.role == Roles.ADMIN.value)
            )
            return q.scalars().all()

    async def get_tehpods(self) -> list[Clients]:
        async with self.AsyncSession() as session:
            q = await session.execute(
                select(Clients)
                .join(ClientRole)
                .where(ClientRole.role == Roles.TEHPOD.value)
            )
            return q.scalars().all()

    async def get_users_not_clients(self) -> list[Clients]:
        async with self.AsyncSession() as session:
            q = await session.execute(
                select(Clients)
                .join(ClientRole)
                .where(ClientRole.role != Roles.USER.value)
            )
            return q.scalars().all()

    async def get_autologin_cashes(self, user_id: str) -> list[ArtixAutologin]:
        async with self.AsyncSession() as session:
            q = await session.execute(
                select(ArtixAutologin).where(ArtixAutologin.user_id == user_id)
            )
            return q.scalars().all()

    async def get_autologin_for_notify(
            self, shopcode: str, cashcode: str
    ) -> list[ArtixAutologin]:
        async with self.AsyncSession() as session:
            admins = await session.execute(
                select(ClientRole).where(
                    ClientRole.role.in_([Roles.ADMIN.value, Roles.TEHPOD.value])
                )
            )
            q = await session.execute(
                select(ArtixAutologin).where(
                    ArtixAutologin.shopcode == shopcode,
                    ArtixAutologin.cashcode == cashcode,
                    ArtixAutologin.user_id.notin_(
                        [admin.user_id for admin in admins.scalars().all()]
                    ),
                )
            )
            return q.scalars().all()

    async def update_client_info(self, **kwargs):
        async with self.AsyncSession() as session:
            q_client = await session.execute(
                select(Clients).where(Clients.user_id == kwargs["user_id"])
            )
            client = q_client.scalars().first()
            if client is None:
                SN = Clients(**kwargs)
                role = ClientRole(user_id=kwargs["user_id"], role=Roles.USER.value)
                session.add(SN)
                session.add(role)
            else:
                await session.execute(
                    update(Clients)
                    .where(Clients.user_id == kwargs["user_id"])
                    .values(**kwargs)
                )
            await session.commit()

    async def add_role_to_all_clients(self):
        async with self.AsyncSession() as session:
            q_client = await session.execute(select(Clients))
            clients = q_client.scalars().all()
            for client in clients:
                if client.role is None:
                    await session.execute(
                        insert(ClientRole).values(
                            user_id=client.user_id, role=Roles.USER.value
                        )
                    )
            await session.commit()


async def get_ttn_log(id: int):
    with Session() as session:
        return session.execute(select(LogsTTN).where(LogsTTN.id > id)).scalars().all()


async def get_ostatki_log(id: int):
    with Session() as session:
        return (
            session.execute(select(LogsOstatki).where(LogsOstatki.id > id))
            .scalars()
            .all()
        )


async def get_goods_log(id: int):
    with Session() as session:
        return (
            session.execute(select(LogsGoods).where(LogsGoods.id > id)).scalars().all()
        )


async def get_inventory_log(id: int):
    with Session() as session:
        return (
            session.execute(select(LogsInventory).where(LogsInventory.id > id))
            .scalars()
            .all()
        )


async def get_edoTTN_log(id: int):
    with Session() as session:
        return (
            session.execute(select(LogsAcceptEDO).where(LogsAcceptEDO.id > id))
            .scalars()
            .all()
        )


async def create_ttn_log(**kwargs):
    with Session() as session:
        log = LogsTTN(**kwargs)
        session.add(log)
        session.commit()


async def create_goods_log(**kwargs):
    with Session() as session:
        log = LogsGoods(**kwargs)
        session.add(log)
        session.commit()


async def create_inventory_log(**kwargs):
    with Session() as session:
        log = LogsInventory(**kwargs)
        session.add(log)
        session.commit()


async def create_ostatki_log(**kwargs):
    with Session() as session:
        log = LogsOstatki(**kwargs)
        session.add(log)
        session.commit()


async def create_edoTTN_log(**kwargs):
    with Session() as session:
        log = LogsAcceptEDO(**kwargs)
        session.add(log)
        session.commit()


async def get_all_client():
    with Session() as session:
        return session.execute(select(Clients)).scalars().all()


async def get_uniq_comps():
    """Возвращает кортеж('Cash', "cash_number user_ids ip")"""
    clients = await get_all_client()
    comp_info = namedtuple("Cash", "cash_number user_ids ip")
    # Уникальные номера компов
    comps = list(
        set(
            [
                comp
                for client in clients
                if client.cash is not None and not client.admin
                for comp in client.cash.split(",")
            ]
        )
    )

    caches = []
    for cash in comps:
        ids = []
        cash_info = get_cash_info(cash.split("-")[1])
        for client in clients:
            if client.cash is not None and not client.admin:
                for comp_client in client.cash.split(","):
                    if comp_client == cash:
                        ids.append(client.user_id)
        caches.append(comp_info(cash, ids, cash_info.ip))
    return caches


async def get_barcodes_for_add(cash_number: str) -> Sequence[Barcodes]:
    with Session() as session:
        barcodes = (
            session.execute(
                select(Barcodes).where(
                    (Barcodes.cash_number == cash_number)
                    & (Barcodes.status == BarcodesStatus.add)
                    & (Barcodes.succes == False)
                )
            )
            .scalars()
            .all()
        )
        return barcodes


async def get_barcodes_for_price(cash_number: str) -> Sequence[Barcodes]:
    with Session() as session:
        barcodes = (
            session.execute(
                select(Barcodes).where(
                    (Barcodes.cash_number == cash_number)
                    & (Barcodes.status == BarcodesStatus.setprice)
                    & (Barcodes.succes == False)
                )
            )
            .scalars()
            .all()
        )
        return barcodes


async def get_barcodes_for_draftbeer(cash_number: str) -> Sequence[Barcodes]:
    with Session() as session:
        barcodes = (
            session.execute(
                select(Barcodes).where(
                    (Barcodes.cash_number == cash_number)
                    & (Barcodes.status == BarcodesStatus.draftbeer)
                    & (Barcodes.succes == False)
                )
            )
            .scalars()
            .all()
        )
        return barcodes


async def update_status_barcode(id: str, state: bool):
    with Session() as session:
        session.execute(update(Barcodes).where(Barcodes.id == id).values(succes=state))
        session.commit()


def get_unique_cashnumbers_from_barcodes():
    with Session() as session:
        return (
            session.execute(
                select(Barcodes.cash_number.distinct()).where(Barcodes.succes == False)
            )
            .scalars()
            .all()
        )


async def get_client_info(chat_id: Union[str, int]) -> Union[bool, Clients]:
    try:
        with Session() as session:
            client = (
                session.query(Clients)
                .options(
                    joinedload(Clients.autologins),
                    joinedload(Clients.role),
                )
                .filter_by(chat_id=str(chat_id))
                .first()
            )
            if client is None:
                return False
            return client
    except OperationalError as ex:
        await get_client_info(chat_id)


async def add_artix_autologin(cash: ForemanCash, user_id: int):
    with Session() as session:
        autologin = ArtixAutologin(
            inn=cash.inn if cash.inn else cash.inn2,
            shopcode=cash.shopcode,
            cashcode=cash.cashcode,
            user_id=user_id,
        )
        session.add(autologin)
        session.commit()


async def del_tg_client(user_id: int):
    with Session() as session:
        session.query(Referrals).filter(Referrals.user_id == str(user_id)).delete()
        session.commit()
        session.query(ArtixAutologin).filter(
            ArtixAutologin.user_id == str(user_id)
        ).delete()
        session.commit()
        session.query(Clients).filter(Clients.user_id == str(user_id)).delete()
        session.commit()


async def del_artix_autologin(id: int):
    with Session() as session:
        session.query(ArtixAutologin).filter(ArtixAutologin.id == id).delete()
        session.commit()

async def del_artix_autologins(list_id: list[int]):
    with Session() as session:
        session.query(ArtixAutologin).filter(ArtixAutologin.id.in_(list_id)).delete()
        session.commit()


async def add_client_cashNumber(**kwargs):
    with Session() as session:
        chat_id = str(kwargs["chat_id"])
        cash = str(kwargs["cash"])
        client = session.query(Clients).filter(Clients.chat_id == chat_id).first()
        if client.cash is None:
            session.query(Clients).filter(Clients.chat_id == chat_id).update(
                kwargs, synchronize_session="fetch"
            )
        else:
            cashes = client.cash.split(",")
            if not cash in cashes:
                cashes = f"{cash},{client.cash}"
                session.query(Clients).filter(Clients.chat_id == chat_id).update(
                    {"chat_id": chat_id, "cash": cashes}, synchronize_session="fetch"
                )
        session.commit()


async def check_cashNumber(chat_id: str, cash: str):
    with Session() as session:
        client = session.query(Clients).filter(Clients.chat_id == chat_id).first()
        if client.cash is None:
            return False
        else:
            cashes = client.cash.split(",")
            if not cash in cashes:
                return False
        return True


async def create_more_barcodes(goods: _Goods, cash: str):
    with Session() as session:
        for product in goods.products:
            session.add(
                Barcodes(
                    cash_number=cash,
                    bcode=product.bcode,
                    name=product.name,
                    op_mode=product.op_mode,
                    measure=product.measure,
                    dcode=product.dcode.value,
                    tmctype=product.tmctype.value,
                    qdefault=product.qdefault,
                    price=product.price,
                )
            )
        session.commit()


async def create_barcode(**kwargs):
    with Session() as session:
        barcode = Barcodes(**kwargs)
        session.add(barcode)
        session.commit()


async def check_cash_in_whitelist(cash_number: str):
    """Проверка номера компьютера в белом списке для приёма ТТН"""
    with Session() as session:
        return session.execute(
            select(Whitelist).where(Whitelist.cash_number == cash_number)
        ).first()


async def get_cash_in_whitelist():
    """Отдаёт номера компьютеров белого списка для приёма ТТН"""
    with Session() as session:
        return session.execute(select(Whitelist)).scalars().all()


async def check_cash_in_acceptlist(cash_number: str) -> Acceptlist:
    """Проверка номера компьютера которые могут принимать ТТН без сканирования"""
    with Session() as session:
        return (
            session.execute(
                select(Acceptlist).where(Acceptlist.cash_number == cash_number)
            )
            .scalars()
            .first()
        )


async def update_cash_in_acceptlist(cash: Acceptlist):
    with Session() as session:
        session.execute(
            update(Acceptlist)
            .where(Acceptlist.cash_number == cash.cash_number)
            .values(
                inn=cash.inn,
                kpp=cash.kpp,
                accept_all_inn=cash.accept_all_inn,
                may_accept_inn=cash.may_accept_inn,
            )
        )
        session.add(cash)
        session.commit()


async def add_cash_in_whitelist(cash_number: str, inn: str):
    """Добавляет номер компьютера в белый список для приёма ТТН"""
    with Session() as session:
        session.execute(insert(Whitelist).values(cash_number=cash_number, inn=inn))
        session.commit()


async def delete_cash_from_whitelist(cash_number: str):
    """Удалить номер компьютера из белого списка приёма ТТН"""
    with Session() as session:
        session.execute(delete(Whitelist).where(Whitelist.cash_number == cash_number))
        session.commit()


async def check_inn_in_blacklist(inn: str):
    """Проверка ИНН в черном списке для приёма ТТН"""
    with Session() as session:
        return session.execute(
            select(BlackInnList).where(BlackInnList.inn == inn)
        ).first()


async def get_whitelist_admins():
    """Забираю админов которые могут добавлять компы в белый список"""
    with Session() as session:
        return (
            session.execute(select(Clients).where(Clients.whitelist_admin))
            .scalars()
            .all()
        )


async def add_referrals(
        ref_id: str, user_id: str, shopcode: int, cashcode: int
) -> None:
    """Добавляет номер компьютера в список которые могут принимать ТТН без сканирования"""
    with Session() as session:
        session.execute(
            insert(Referrals).values(
                ref_id=ref_id, user_id=user_id, shopcode=shopcode, cashcode=cashcode
            )
        )
        session.commit()


def count_onlinechecks(shopcode: int, cashcode: int) -> int:
    """Количество созданных онлайн чеков у конкретного магазина и кассы"""
    with Session() as session:
        count = session.execute(
            select(OnlineChecks).filter(
                OnlineChecks.shopcode == shopcode,
                OnlineChecks.cashcode == cashcode,
            )
        ).all()
    return len(count)


async def save_onlinecheck(
        csid: str,
        user_id: str,
        shopcode: int,
        cashcode: int,
        documentid: str,
        type: OnlineCheckType = OnlineCheckType.TTN,
) -> None:
    """Список созданных онлайн чеков у конкретного магазина и кассы"""
    with Session() as session:
        session.execute(
            insert(OnlineChecks).values(
                csid=csid,
                user_id=user_id,
                shopcode=shopcode,
                cashcode=cashcode,
                documentid=documentid,
                type=type,
            )
        )
        session.commit()


async def test():
    db = Database()
    cashes = await db.get_users_not_clients()
    for cash in cashes:
        print(cash.first_name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(test())
