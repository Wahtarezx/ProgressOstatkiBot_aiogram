from typing import Union, Type
from sqlalchemy.exc import OperationalError
from sqlalchemy import create_engine, update, insert, inspect, func, text
from sqlalchemy.orm import sessionmaker, aliased

import config
from core.database.artix.model import *
from core.loggers.make_loggers import bot_log
from core.services.egais.goods.pd_models import _Goods, TmcType, UpdateHotkeyType
from core.utils import texts


class ArtixCashDB:
    def __init__(self, ip: str, database: str = "dictionaries"):
        self.engine = create_engine(
            f"mysql+pymysql://{config.cash_user}:{config.cash_password}@{ip}:{config.port}/{database}?charset=utf8mb4",
            pool_recycle=3600,
            pool_timeout=30,
        )
        bot_log.debug(f'ArtixCashDB - Подключаюсь к БД {self.engine.url}')
        self.Session = sessionmaker(bind=self.engine)
        self.ip = ip

    def ping(self) -> None:
        with self.Session() as session:
            session.query(text("SELECT 1"))

    def get_main_actiopanelitems(
        self, name="Товары"
    ) -> list[Actionpanel, Actionpanelitem, Actionparameter]:
        with self.Session() as session:
            actionpanel_alias = aliased(Actionpanel)
            actionpanelitem_alias = aliased(Actionpanelitem)
            actionparameter_alias = aliased(Actionparameter)
            query = (
                session.query(
                    actionpanel_alias, actionpanelitem_alias, actionparameter_alias
                )
                .join(
                    actionpanelitem_alias,
                    actionpanel_alias.actionpanelcode
                    == actionpanelitem_alias.actionpanelcode,
                )
                .join(
                    actionparameter_alias,
                    actionpanelitem_alias.actioncode
                    == actionparameter_alias.cmactioncode,
                )
                .where(actionpanelitem_alias.name.like(f"%{name}%"))
            )
            return query.all()

    def get_actionpanelitems(
        self, actionpanelcode: int = 5, context: int = 6, page: int = 2
    ) -> list[Actionpanel, Actionpanelitem, Actionparameter]:
        with self.Session() as session:
            actionpanel_alias = aliased(Actionpanel)
            actionpanelitem_alias = aliased(Actionpanelitem)
            actionparameter_alias = aliased(Actionparameter)
            query = (
                session.query(
                    actionpanel_alias, actionpanelitem_alias, actionparameter_alias
                )
                .join(
                    actionpanelitem_alias,
                    actionpanel_alias.actionpanelcode
                    == actionpanelitem_alias.actionpanelcode,
                )
                .join(
                    actionparameter_alias,
                    actionpanelitem_alias.actioncode
                    == actionparameter_alias.cmactioncode,
                )
                .where(
                    actionpanelitem_alias.actionpanelcode == actionpanelcode,
                    actionpanel_alias.context == context,
                    actionpanel_alias.page == page,
                )
            )
            return query.all()

    def get_actionpanel_by_context_and_page(
        self, context: int, page: int
    ) -> Union[Actionpanel, None]:
        with self.Session() as session:
            drbr_panel = (
                session.query(Actionpanel)
                .where(Actionpanel.context == context, Actionpanel.page == page)
                .first()
            )
            return drbr_panel

    def get_actionPanelItems_draftbeer(
        self,
    ) -> list[Actionpanel, Actionpanelitem, Actionparameter]:
        """
        Все кнопки внутри категории "Пиво", которые имеют actionparameter
        :return:
        """
        current_context, nextpage = None, None
        for actionpanel, actionpanelitem, actionparametr in self.get_actionpanelitems():
            if (
                "пиво" in actionpanelitem.name.lower()
                and actionparametr.parametername == "page"
            ):
                nextpage = actionparametr.parametervalue
                current_context = actionpanel.context
                break
        if current_context is None:
            raise ValueError("Не найдена категория <b><u>Пиво</u></b>")

        apanel = self.get_actionpanel_by_context_and_page(current_context, nextpage)
        return self.get_actionpanelitems(
            actionpanelcode=apanel.actionpanelcode,
            context=apanel.context,
            page=apanel.page,
        )

    def get_actionpanelitem(
        self, actionpanelitemcode: int
    ) -> Union[Actionpanelitem, None]:
        with self.Session() as session:
            q = (
                session.query(Actionpanelitem)
                .where(Actionpanelitem.actionpanelitemcode == actionpanelitemcode)
                .first()
            )
            return q

    def get_actionpanelparameter(self, actioncode: int) -> Union[Actionparameter, None]:
        with self.Session() as session:
            q = (
                session.query(Actionparameter)
                .where(Actionparameter.cmactioncode == actioncode)
                .first()
            )
            return q

    def get_hotkey(self, hotkeycode: int) -> Union[Hotkey, None]:
        with self.Session() as session:
            q = session.query(Hotkey).where(Hotkey.hotkeycode == hotkeycode).first()
            return q

    def get_hotkeyinvents(self, hotkeycode: int) -> Union[list[HotkeyInvent], None]:
        with self.Session() as session:
            q = (
                session.query(HotkeyInvent)
                .where(HotkeyInvent.hotkeycode == hotkeycode)
                .all()
            )
            return q if len(q) > 0 else None

    async def add_products_in_cash(self, good: _Goods):
        for product in good.products:
            if product.touch is not None:
                if product.touch.type == UpdateHotkeyType.UPDATE:
                    await self.update_name_actionpanelitem(
                        product.name, product.touch.actionpanelitem.actionpanelitemcode
                    )
                    await self.update_or_add_bcode_hotkeyinvent(
                        product.bcode, product.touch.hotkey.hotkeycode
                    )
                if product.touch.type == UpdateHotkeyType.APPEND:
                    await self.add_hotkeyinvent(
                        product.bcode, product.touch.hotkey.hotkeycode
                    )
            if product.tmctype == TmcType.draftbeer:
                await self.insert_draftbeer_ostatki(
                    cis=product.cis,
                    bcode=product.bcode,
                    name=product.name,
                    expirationdate=product.draftbeer.expirationDate,
                    volume=product.draftbeer.volume_draftbeer,
                )

    async def update_name_actionpanelitem(self, name: str, actionpanelitemcode: int):
        with self.Session() as s:
            s.execute(
                update(Actionpanelitem)
                .where(Actionpanelitem.actionpanelitemcode == actionpanelitemcode)
                .values(name=name)
            )
            s.commit()

    async def update_or_add_bcode_hotkeyinvent(self, bcode: str, hotkeycode: int):
        print(f'Штрихкод: {bcode}')
        with self.Session() as s:
            invent = (
                s.query(HotkeyInvent)
                .where(HotkeyInvent.hotkeycode == hotkeycode)
                .first()
            )
            if invent is not None:
                s.execute(
                    update(HotkeyInvent)
                    .where(HotkeyInvent.hotkeycode == hotkeycode)
                    .values(inventcode=bcode)
                )
            else:
                s.execute(
                    insert(HotkeyInvent).values(
                        inventcode=bcode,
                        hotkeycode=hotkeycode,
                    )
                )
            s.commit()

    async def add_hotkeyinvent(self, bcode: str, hotkeycode: int) -> None:
        with self.Session() as s:
            hotkey_invents = (
                s.query(HotkeyInvent).where(HotkeyInvent.hotkeycode == hotkeycode).all()
            )
            if bcode in [h.inventcode for h in hotkey_invents]:
                return
            s.execute(
                insert(HotkeyInvent).values(
                    inventcode=bcode,
                    hotkeycode=hotkeycode,
                )
            )
            s.commit()

    async def insert_draftbeer_ostatki(
        self,
        cis: str,
        bcode: str,
        name: str,
        expirationdate: datetime,
        volume: float,
        connectdate: datetime = None,
    ):
        try:
            if connectdate is None:
                connectdate = datetime.now()
            with self.Session() as s:
                already_cis = (
                    s.query(Remaindraftbeer)
                    .where(Remaindraftbeer.markingcode == cis)
                    .first()
                )
                if already_cis is None:
                    s.execute(
                        insert(Remaindraftbeer).values(
                            markingcode=cis,
                            barcode=bcode,
                            name=name,
                            expirationdate=expirationdate,
                            connectdate=connectdate,
                            volume=volume,
                        )
                    )
                # elif already_cis.volume == 0:
                else:
                    s.execute(
                        update(Remaindraftbeer)
                        .where(Remaindraftbeer.markingcode == cis)
                        .values(
                            markingcode=cis,
                            barcode=bcode,
                            name=name,
                            connectdate=connectdate,
                            expirationdate=expirationdate,
                            volume=volume,
                        )
                    )
                s.commit()
        except OperationalError:
            raise ConnectionError(texts.error_cashNotOnline)

    async def check_table(self, table_name) -> bool:
        inspector = inspect(self.engine)
        table_exists = table_name in inspector.get_table_names()
        return True if table_exists else False

    async def get_tmc(self, bcode: str) -> Union[TMC, None]:
        with self.Session() as session:
            return session.query(TMC).where(TMC.bcode == bcode).first()

    async def update_tmc(self, **kwargs) -> None:
        with self.Session() as session:
            session.execute(
                update(TMC).where(TMC.bcode == str(kwargs["bcode"])).values(**kwargs)
            )
            session.commit()

    async def insert_tmc(self, **kwargs) -> None:
        with self.Session() as session:
            session.execute(insert(TMC).values(**kwargs))
            session.commit()

    async def get_barcode(self, bcode: str) -> Union[BARCODES, None]:
        with self.Session() as session:
            return session.query(BARCODES).where(BARCODES.barcode == bcode).first()

    async def update_barcode(self, **kwargs) -> None:
        with self.Session() as session:
            session.execute(
                update(BARCODES)
                .where(BARCODES.barcode == str(kwargs["barcode"]))
                .values(**kwargs)
            )
            session.commit()

    async def insert_barcode(self, **kwargs) -> None:
        with self.Session() as session:
            session.execute(insert(BARCODES).values(**kwargs))
            session.commit()

    async def get_all_units(self) -> list[Type[Units]]:
        with self.Session() as session:
            return session.query(Units).all()

    async def get_unit(self, code: int) -> Type[Units] | None:
        with self.Session() as session:
            return session.query(Units).where(Units.code == code).first()

    async def get_unit_by_frunit(self, frunit: int) -> Type[Units] | None:
        with self.Session() as session:
            return session.query(Units).where(Units.frunit == frunit).first()

    async def insert_unit(self, name: str, flag: int, frunit: int) -> None:
        with self.Session() as session:
            session.execute(
                insert(Units).values(
                    name=name,
                    flag=flag,
                    frunit=frunit,
                )
            )
            session.commit()

    async def create_mol(self, fio: str) -> int:
        """Возвращает код созданного пользователя"""
        with self.Session() as session:
            max_code = session.query(func.max(MOL.code)).scalar()
            session.execute(
                insert(MOL).values(
                    code=str(int(max_code) + 1),
                    login=str(int(max_code) + 1),
                    password=str(int(max_code) + 1),
                    name=fio,
                )
            )
            session.execute(
                insert(RoleUser).values(
                    usercode=str(int(max_code) + 1),
                )
            )
            session.commit()
            return int(max_code) + 1

    async def get_all_mols(self) -> list[Type[MOL]]:
        with self.Session() as session:
            return session.query(MOL).all()

    async def get_all_valuts(self) -> list[Type[Valut]]:
        with self.Session() as session:
            return session.query(Valut).all()

    async def get_valut(self, code: int) -> Type[Valut] | None:
        with self.Session() as session:
            return session.query(Valut).where(Valut.code == code).first()

    async def get_valut_by_name(self, name: str) -> Type[Valut] | None:
        with self.Session() as session:
            return session.query(Valut).where(Valut.name.like(f"%{name}%")).first()

    async def get_excise_from_whitelist(
        self, excise: str
    ) -> Type[Excisemarkwhite] | None:
        with self.Session() as session:
            return (
                session.query(Excisemarkwhite)
                .where(Excisemarkwhite.excisemarkid.like(f"%{excise}%"))
                .first()
            )


if __name__ == "__main__":
    import asyncio

    artix = ArtixCashDB("10.8.32.50")
    for (
        actionpanel,
        actionpanelitem,
        actionpanelparameter,
    ) in artix.get_actionpanelitems():
        if actionpanelparameter.parametername == "hotKeyCode":
            hotkey = artix.get_hotkey(actionpanelparameter.parametervalue)
            print(artix.get_hotkeyinvents(hotkey.hotkeycode))
