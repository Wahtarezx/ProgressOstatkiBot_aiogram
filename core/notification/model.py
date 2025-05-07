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


class NotifiTTN(Base):
    __tablename__ = "nofitication_ttn"
    id = Column(BigInteger, nullable=False, primary_key=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    cash_number = Column(String(50), nullable=False)
    user_id = Column(String(50), nullable=False)
    ttn_egais = Column(String(50))
    ttn_date = Column(String(50))
    ttn_number = Column(String(50))
    shipper_fsrar = Column(String(50))
    send = Column(Boolean, default=False)
    title = Column(String(500))


class NotifiRutoken(Base):
    __tablename__ = "nofitication_rutoken"
    id = Column(BigInteger, nullable=False, primary_key=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    cash_number = Column(String(50), nullable=False)
    user_id = Column(String(50), nullable=False)
    rutoken_date = Column(String(50))
    days_left = Column(String(5))
    ooo_name = Column(String(50))
    send = Column(Boolean, default=False)
    title = Column(String(500))


Base.metadata.create_all(engine)
