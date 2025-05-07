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
    Enum,
    ForeignKey,
    TEXT,
)
from sqlalchemy.orm import relationship

import config
from sqlalchemy.sql import func

engine = create_engine(
    f"mysql+pymysql://{config.db_user}:{config.db_password}@{config.ip}:{config.port}/{config.bot_database}?charset=utf8mb4",
    pool_recycle=3600,
    pool_timeout=30,
)
Base = sqlalchemy.orm.declarative_base()


class OnlineCheckType(enum.Enum):
    TTN = "TTN"
    DEGUSTATION = "DEGUSTATION"
    BASIC = "BASIC"


class Clients(Base):
    __tablename__ = "clients"
    date = Column(DateTime(timezone=True), server_default=func.now())
    phone_number = Column(String(50), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    user_id = Column(String(50), primary_key=True)
    chat_id = Column(String(50), nullable=False)
    cash = Column(String(10000))
    admin = Column(Boolean, default=False)
    whitelist_admin = Column(Boolean, default=False)
    accept_admin = Column(Boolean, default=False)
    edo_admin = Column(Boolean, default=False)

    autologins = relationship(
        "ArtixAutologin", back_populates="client", cascade="delete, delete-orphan"
    )
    referrals = relationship(
        "Referrals",
        foreign_keys="[Referrals.user_id]",
        back_populates="client",
        cascade="delete, delete-orphan",
    )
    referred_by = relationship(
        "Referrals", foreign_keys="[Referrals.ref_id]", back_populates="referrer"
    )
    onlinechecks = relationship(
        "OnlineChecks", back_populates="client", cascade="delete, delete-orphan"
    )
    role = relationship(
        "ClientRole",
        back_populates="client",
        cascade="delete, all",
        lazy="joined",
        uselist=False,
    )


class ClientRole(Base):
    __tablename__ = "client_role"
    id = Column(BigInteger, nullable=False, primary_key=True)
    role = Column(String(50), nullable=False)
    user_id = Column(String(50), ForeignKey("clients.user_id"), nullable=False)

    client = relationship("Clients", back_populates="role")


class BarcodesStatus(enum.Enum):
    add = 1  # Добавить в бд кассы
    setprice = 2  # Изменить цену товара
    draftbeer = 3  # Добавить разливное пиво


class Barcodes(Base):
    __tablename__ = "barcodes"
    id = Column(BigInteger, nullable=False, primary_key=True)
    cash_number = Column(String(50), nullable=False)
    bcode = Column(String(50), nullable=False)
    cis = Column(String(50))
    name = Column(String(300))
    op_mode = Column(Integer())
    measure = Column(Integer())
    dcode = Column(Integer())
    tmctype = Column(Integer())
    qdefault = Column(Integer())
    price = Column(String(20))
    status = Column(Enum(BarcodesStatus, native_enum=False), default=BarcodesStatus.add)
    comment = Column(String(200))
    succes = Column(Boolean(), default=False)


class Whitelist(Base):
    __tablename__ = "cash_whitelist"
    id = Column(BigInteger, nullable=False, primary_key=True)
    cash_number = Column(String(50), nullable=False)
    inn = Column(String(50), nullable=False)


class Acceptlist(Base):
    __tablename__ = "cash_acceptlist"
    id = Column(BigInteger, nullable=False, primary_key=True)
    cash_number = Column(String(50), nullable=False)
    inn = Column(String(50), nullable=False)
    kpp = Column(String(50), nullable=False)
    accept_all_inn = Column(Boolean(), default=True)
    may_accept_inn = Column(TEXT(), default="[]")


class BlackInnList(Base):
    __tablename__ = "black_inn_list"
    id = Column(BigInteger, nullable=False, primary_key=True)
    inn = Column(String(50), nullable=False)


class ArtixAutologin(Base):
    __tablename__ = "artix_autologin"
    id = Column(BigInteger, primary_key=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    shopcode = Column(Integer, nullable=False)
    cashcode = Column(Integer, nullable=False)
    user_id = Column(String(50), ForeignKey("clients.user_id"), nullable=False)
    inn = Column(String(50), nullable=False)
    client = relationship("Clients", back_populates="autologins")


class Referrals(Base):
    __tablename__ = "referrals"
    id = Column(BigInteger, primary_key=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    shopcode = Column(Integer, nullable=False)
    cashcode = Column(Integer, nullable=False)
    user_id = Column(String(50), ForeignKey("clients.user_id"), nullable=False)
    ref_id = Column(String(50), ForeignKey("clients.user_id"), nullable=False)
    inn = Column(String(50), nullable=True)
    client = relationship("Clients", foreign_keys=[user_id], back_populates="referrals")
    referrer = relationship(
        "Clients", foreign_keys=[ref_id], back_populates="referred_by"
    )


class OnlineChecks(Base):
    __tablename__ = "onlinechecks"
    id = Column(BigInteger, primary_key=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    shopcode = Column(Integer, nullable=False)
    cashcode = Column(Integer, nullable=False)
    documentid = Column(String(50), nullable=False, comment="ID чека")
    user_id = Column(
        String(50),
        ForeignKey("clients.user_id"),
        nullable=False,
        comment="ID пользователя телеграм",
    )
    csid = Column(String(50), nullable=False, comment="ID в ответ на создание чека")
    type = Column(
        Enum(OnlineCheckType),
        default=OnlineCheckType.TTN,
        nullable=False,
        comment="Тип чека",
    )
    client = relationship("Clients", back_populates="onlinechecks")


Base.metadata.create_all(engine)
