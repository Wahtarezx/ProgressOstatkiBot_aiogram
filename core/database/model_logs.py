import enum

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
    Enum,
)
from sqlalchemy.orm import relationship

import config
from sqlalchemy.sql import func

from core.services.markirovka.enums import GisMtDocType

engine = create_engine(
    f"mysql+pymysql://{config.db_user}:{config.db_password}@{config.ip}:{config.port}/{config.bot_database}?charset=utf8mb4",
    pool_recycle=3600,
    pool_timeout=30,
)
Base = sqlalchemy.orm.declarative_base()


class Level(enum.Enum):
    success = "SUCCESS"
    error = "ERROR"
    warning = "WARNING"
    info = "INFO"
    debug = "DEBUG"


class LogsTTN(Base):
    Category = {
        "type": [
            "Подтвердить",
            "Расхождение",
            "Перевыслать",
        ]
    }
    __tablename__ = "logs_ttn"
    id = Column(BigInteger, nullable=False, primary_key=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    cash_number = Column(String(50), nullable=False)
    user_id = Column(String(50))
    level = Column(String(50), nullable=False)
    type = Column(String(200), nullable=False)
    inn = Column(String(50))
    ttns_egais = Column(String(50))
    shipper_inn = Column(String(50))
    shipper_fsrar = Column(String(50))
    description = Column(String(500))


class LogsGoods(Base):
    Category = {
        "type": [
            "Сгенерировали",
            "Изменили цену",
            "Добавили",
        ]
    }
    __tablename__ = "logs_goods"
    id = Column(BigInteger, nullable=False, primary_key=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    cash_number = Column(String(50), nullable=False)
    level = Column(String(50), nullable=False)
    type = Column(String(200), nullable=False)
    inn = Column(String(50))
    user_id = Column(String(50))
    bcode = Column(String(50))
    op_mode = Column(String(50))
    qdefault = Column(String(50))
    tmctype = Column(String(50))
    otdel = Column(String(50))
    price = Column(String(50))
    description = Column(String(500))


class LogsInventory(Base):
    __tablename__ = "logs_inventory"
    id = Column(BigInteger, nullable=False, primary_key=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    cash_number = Column(String(50), nullable=False)
    user_id = Column(String(50))
    level = Column(String(50), nullable=False)
    inn = Column(String(50), nullable=False)
    phone = Column(String(50), nullable=False)
    count_bottles = Column(String(50), nullable=False)
    file_path = Column(String(500))
    description = Column(String(500))


class LogsOstatki(Base):
    __tablename__ = "logs_ostatki"
    id = Column(BigInteger, nullable=False, primary_key=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    cash_number = Column(String(50), nullable=False)
    user_id = Column(String(50))
    level = Column(String(50), nullable=False)
    inn = Column(String(50), nullable=False)
    file_path = Column(String(500), nullable=False)
    description = Column(String(500))


class LogsAcceptEDO(Base):
    Category = {
        "operation_type": [
            "Подтвердить",
            "...",
            "...",
        ]
    }
    __tablename__ = "logs_edottn"
    id = Column(BigInteger, nullable=False, primary_key=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    fio = Column(String(250))
    user_id = Column(String(50))
    level = Column(String(50), nullable=False)
    operation_type = Column(String(200), nullable=False)
    inn = Column(String(50))
    doc_type = Column(String(50))
    shipper_inn = Column(String(50))
    shipper_kpp = Column(String(50))
    shipper_name = Column(String(250))
    edo_provider = Column(Integer())
    description = Column(String(500))


class LogsEdoDocuments(Base):
    __tablename__ = "logs_edodocuments"
    id = Column(BigInteger, nullable=False, primary_key=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    fio = Column(String(250))
    user_id = Column(String(50))
    level = Column(Enum(Level))
    doc_type = Column(Enum(GisMtDocType))
    doc_id = Column(String(200), nullable=False)
    inn = Column(String(50))
    description = Column(String(500))


Base.metadata.create_all(engine)
