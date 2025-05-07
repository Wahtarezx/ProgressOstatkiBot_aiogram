from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from core.database.model import *
import config
from typing import Union

from core.database.modelBOT import OnlineChecks

engine = create_engine(
    f"mysql+pymysql://{config.db_user}:{config.db_password}@{config.ip}:{config.port}/{config.progress_database}?charset=utf8mb4",
    pool_recycle=3600,
    pool_timeout=30,
)
Session = sessionmaker(bind=engine)


def get_cash_info(cash_number) -> Union[bool, CashInfo]:
    with Session() as session:
        q = session.execute(
            select(CashInfo).filter(CashInfo.name.ilike(f"%cash-{cash_number}-%"))
        )
        if q is None:
            return False
        return q.scalars().first()


def get_cash_info_by_inn(inn):
    with Session() as session:
        q = session.execute(select(CashInfo).filter(CashInfo.ip_inn == str(inn)))
        if q is not None:
            return q.scalars().first()
        q = session.execute(select(CashInfo).filter(CashInfo.inn == str(inn)))
        if q is not None:
            return q.scalars().first()


def check_cash_info(cash_number):
    with Session() as session:
        q = session.execute(
            select(CashInfo).filter(CashInfo.name.ilike(f"%cash-{cash_number}-%"))
        )
        if q is None:
            return False
        return len(q.fetchall())


def get_shipper_info(fsrar: str = None, inn: str = None):
    with Session() as session:
        if inn is None:
            q = session.execute(select(Shippers).filter(Shippers.fsrar == fsrar))
        else:
            q = session.execute(select(Shippers).filter(Shippers.inn == inn))
        if q is None:
            return False
        return q.scalars().first()


if __name__ == "__main__":
    print(get_cash_info_by_inn(123))
