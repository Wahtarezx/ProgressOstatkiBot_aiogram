import sqlalchemy.orm
from sqlalchemy import (
    create_engine,
    String,
    Column,
    DateTime,
    Boolean,
    BigInteger,
    Integer,
    Identity,
)
import config
from sqlalchemy.sql import func

engine = create_engine(
    f"mysql+pymysql://{config.db_user}:{config.db_password}@{config.ip}:{config.port}/{config.bot_database}?charset=utf8mb4"
)
Base = sqlalchemy.orm.declarative_base()


class CashInfo(Base):
    __tablename__ = "cash_info"

    id = Column(BigInteger, nullable=False, primary_key=True)
    name = Column(String(255), nullable=False)
    inn = Column(String(255), nullable=False)
    kpp = Column(String(255), nullable=False)
    fsrar = Column(String(255))
    fsrar2 = Column(String(255))
    address = Column(String(255), nullable=False)
    ooo_name = Column(String(255))
    ip_name = Column(String(255))
    ip_inn = Column(String(255))
    ip = Column(String(255))
    touch_panel = Column(Boolean(), default=False)


class Shippers(Base):
    __tablename__ = "shippers"
    id = Column(Integer, nullable=False, primary_key=True)
    name = Column(
        String(255),
        nullable=False,
    )
    inn = Column(String(255), nullable=False)
    fsrar = Column(String(255), nullable=False)


Base.metadata.create_all(engine)
