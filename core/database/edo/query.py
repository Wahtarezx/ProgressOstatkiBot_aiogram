import sqlalchemy
from sqlalchemy import create_engine, select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

import config
from core.services.markirovka.database.model import AutoLoginMarkirovka

engine = create_engine(
    f"mysql+aiomysql://{config.db_user}:{config.db_password}@{config.ip}:{config.port}/{config.bot_database}?charset=utf8mb4",
    pool_recycle=3600,
    pool_timeout=30,
)
Base = sqlalchemy.orm.declarative_base()
Session = sessionmaker(bind=engine)


class EdoDB:
    def __init__(self):
        self.engine = create_async_engine(config.db_cfg.get_url())
        self.AsyncSession = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def create_autologin(self, autologin: AutoLoginMarkirovka) -> None:
        async with self.AsyncSession() as session:
            q = await session.execute(
                select(AutoLoginMarkirovka).filter(
                    AutoLoginMarkirovka.inn == autologin.inn,
                    AutoLoginMarkirovka.chat_id == autologin.chat_id,
                )
            )
            cert = q.scalars().first()
            if cert is None:
                session.add(autologin)
            await session.commit()

    async def get_markirovka_autologins(
        self, chat_id: int
    ) -> list[AutoLoginMarkirovka]:
        async with self.AsyncSession() as session:
            q = await session.execute(
                select(AutoLoginMarkirovka).filter(
                    AutoLoginMarkirovka.chat_id == str(chat_id)
                )
            )
            return q.scalars().all()

    async def delete_autologin(self, acc_id: int) -> None:
        async with self.AsyncSession() as session:
            await session.execute(
                delete(AutoLoginMarkirovka).where(AutoLoginMarkirovka.id == acc_id)
            )
            await session.commit()
