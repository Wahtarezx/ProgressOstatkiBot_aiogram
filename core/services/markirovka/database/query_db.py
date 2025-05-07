import asyncio
from typing import Type, Any, Sequence

from sqlalchemy import insert, delete, select, Row, RowMapping
from sqlalchemy.orm import *

from core.database.model_logs import LogsEdoDocuments, Level
from core.services.markirovka.database.model import *
from core.services.markirovka.enums import GisMtDocType
from core.services.markirovka.inventory.models import Inventory

engine = create_engine(
    f"mysql+pymysql://{config.db_user}:{config.db_password}@{config.ip}:{config.port}/{config.bot_database}?charset=utf8mb4",
    pool_recycle=3600,
    pool_timeout=30,
)
Session = sessionmaker(bind=engine)


async def select_last_inventory_log(inn: str) -> InventoryLogs:
    with Session() as session:
        return session.scalars(
            select(InventoryLogs)
            .where(InventoryLogs.inn == inn)
            .order_by(InventoryLogs.id.desc())
        ).first()


async def create_inventory_log(chat_id: int, file_path: str, inventory: Inventory):
    with Session() as session:
        session.execute(
            insert(InventoryLogs).values(
                chat_id=str(chat_id),
                file_path=file_path,
                inn=inventory.inn,
                pg_name=inventory.pg_name,
                action=inventory.action,
                primary_document_custom_name=inventory.primary_document_custom_name,
                action_date=inventory.action_date,
                document_type=inventory.document_type,
                document_number=inventory.document_number,
                document_date=inventory.document_date,
            )
        )
        session.commit()


async def create_edodocuments_log(
    user_id: str,
    doc_type: GisMtDocType,
    doc_id: str,
    fio: str,
    level: Level,
    inn: str,
) -> None:
    with Session() as session:
        session.execute(
            insert(LogsEdoDocuments).values(
                user_id=user_id,
                doc_type=doc_type,
                doc_id=doc_id,
                fio=fio,
                level=level,
                inn=inn,
            )
        )
        session.commit()


async def get_znak_profiles_by_chatid(chat_id: str) -> Sequence[AutoLoginMarkirovka]:
    with Session() as session:
        return session.scalars(
            select(AutoLoginMarkirovka).where(AutoLoginMarkirovka.chat_id == chat_id)
        ).all()


async def get_znak_profile(id: int) -> AutoLoginMarkirovka | None:
    with Session() as session:
        return session.scalars(
            select(AutoLoginMarkirovka).where(AutoLoginMarkirovka.id == id)
        ).first()


# endregion
