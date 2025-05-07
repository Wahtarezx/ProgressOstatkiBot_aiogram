import sqlalchemy.orm
from sqlalchemy import (
    create_engine,
    String,
    Column,
    DateTime,
    Boolean,
    Integer,
    BigInteger,
    ForeignKey,
)

from sqlalchemy.sql import func

import config

engine = create_engine(
    f"mysql+pymysql://{config.db_user}:{config.db_password}@{config.ip}:{config.port}/{config.bot_database}?charset=utf8mb4",
    pool_recycle=3600,
    pool_timeout=30,
)
Base = sqlalchemy.orm.declarative_base()


class Certificates(Base):
    """
    edo_provider [
    1 - Честный знак
    2 - Платформа ОФД
    3 - Контур
    ]
    """

    __tablename__ = "certificates"
    id = Column(BigInteger, nullable=False, primary_key=True)
    date_create = Column(DateTime(timezone=True), server_default=func.now())
    thumbprint = Column(String(500), nullable=False)
    cert_from = Column(String(100))
    cert_to = Column(String(100))
    first_name = Column(String(250), nullable=False)
    last_name = Column(String(250), nullable=False)
    patronymic = Column(String(250), nullable=False)
    inn = Column(String(50), nullable=False)
    cert_path = Column(String(500), nullable=False)
    edo_provider = Column(Integer)
    description = Column(String(500))


class AutoLoginMarkirovka(Base):
    __tablename__ = "markirovka_autologin"
    id = Column(BigInteger, nullable=False, primary_key=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    chat_id = Column(String(250), nullable=False)
    inn = Column(String(50), nullable=False)
    kpp = Column(String(50), nullable=True)
    fio = Column(String(250), nullable=False)
    thumbprint = Column(String(500), nullable=False)
    edo_provider = Column(Integer)


class InventoryLogs(Base):
    __tablename__ = "markirovka_inventory_logs"
    id = Column(BigInteger, primary_key=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    chat_id = Column(String(250), nullable=False)
    inn = Column(String(50), nullable=False)
    pg_name = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    primary_document_custom_name = Column(String(50))
    action_date = Column(String(50), nullable=False)
    document_type = Column(String(50), nullable=False)
    document_number = Column(String(50), nullable=False)
    document_date = Column(String(50), nullable=False)
    file_path = Column(String(250), nullable=False)


Base.metadata.create_all(engine)
