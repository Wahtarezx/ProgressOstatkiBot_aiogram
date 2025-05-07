from sqlalchemy import create_engine
from sqlalchemy.orm import *
from sqlalchemy import select, update, insert, delete

import config
from core.notification.model import NotifiTTN, NotifiRutoken

engine = create_engine(
    f"mysql+pymysql://{config.db_user}:{config.db_password}@{config.ip}:{config.port}/{config.bot_database}?charset=utf8mb4",
    pool_recycle=3600,
    pool_timeout=30,
)
Session = sessionmaker(bind=engine)


# region TTN
async def check_exist_ttn(ttn_egais: str, user_id: str):
    with Session() as session:
        return session.execute(
            select(NotifiTTN).where(
                NotifiTTN.ttn_egais == ttn_egais, NotifiTTN.user_id == user_id
            )
        ).first()


async def insert_ttn_notifi(**kwargs):
    with Session() as session:
        session.add(NotifiTTN(**kwargs))
        session.commit()


async def get_all_not_send_ttn_notifi():
    with Session() as session:
        return (
            session.execute(select(NotifiTTN).where(NotifiTTN.send == False))
            .scalars()
            .all()
        )


async def update_to_send_ttn(ttn_egais: str, user_id: str):
    with Session() as session:
        session.execute(
            update(NotifiTTN)
            .where(NotifiTTN.user_id == user_id, NotifiTTN.ttn_egais == ttn_egais)
            .values(send=True)
        )
        session.commit()


# endregion


# region rutoken
async def check_exist_rutoken(rutoken_date: str, user_id: str, days_left: str):
    with Session() as session:
        return session.execute(
            select(NotifiRutoken).where(
                NotifiRutoken.rutoken_date == rutoken_date,
                NotifiRutoken.user_id == user_id,
                NotifiRutoken.days_left == days_left,
            )
        ).first()


async def get_all_not_send_rutoken_notifi():
    with Session() as session:
        return (
            session.execute(select(NotifiRutoken).where(NotifiRutoken.send == False))
            .scalars()
            .all()
        )


async def update_to_send_rutoken(rutoken_date: str, user_id: str):
    with Session() as session:
        session.execute(
            update(NotifiRutoken)
            .where(
                NotifiRutoken.user_id == user_id,
                NotifiRutoken.rutoken_date == rutoken_date,
            )
            .values(send=True)
        )
        session.commit()


async def insert_rutoken_notifi(**kwargs):
    with Session() as session:
        session.add(NotifiRutoken(**kwargs))
        session.commit()


# endregion
