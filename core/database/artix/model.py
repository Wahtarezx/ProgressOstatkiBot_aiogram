import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    Text,
    DateTime,
    Numeric,
    DECIMAL,
    Enum,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ExciseTypeEnum(enum.Enum):
    ALCOHOL = "ALCOHOL"
    TOBACCO = "TOBACCO"
    MEDIC = "MEDIC"
    MARKEDGOODS = "MARKEDGOODS"


class ValutType(enum.Enum):
    nal = "1"  # наличные
    beznal = "2"  # электронные
    avans = "3"  # предварительная оплата (аванс)
    kredit = "4"  # последующая оплата (кредит)
    other = "5"  # иная форма оплаты (встречное представление)


class ValutPayprocmodule(enum.Enum):
    nal = None  # наличные
    zaglushka = "libProcessingDummy"  # Заглушка
    sber = "libProcessingSb"  # Сбербанк>
    ucs = "libProcessingUCS"  # РосБанк UCS
    arcus = "libProcessingArcusMultimerchant"  # РосБанк UCS
    inpas = "libProcessingInpas"  # Инпас


class Hotkey(Base):
    __tablename__ = "hotkey"

    hotkeycode = Column(Integer, primary_key=True)
    hotkeyname = Column(String(100), nullable=False)
    bybarcode = Column(Boolean)


class HotkeyInvent(Base):
    __tablename__ = "hotkeyinvent"

    hotkeyinventid = Column(Integer, primary_key=True)
    inventcode = Column(String(100), nullable=False)
    hotkeycode = Column(Integer)


class Actionpanel(Base):
    __tablename__ = "actionpanel"

    actionpanelcode = Column(Integer, primary_key=True)
    context = Column(Integer, nullable=False)
    page = Column(Integer, nullable=False)
    rowcount = Column(Integer, nullable=False)
    columncount = Column(Integer, nullable=False)


class Actionpanelitem(Base):
    __tablename__ = "actionpanelitem"

    actionpanelitemcode = Column(Integer, primary_key=True)
    name = Column(String(100))
    color = Column(String(20))
    actionpanelcode = Column(Integer, nullable=False)
    actioncode = Column(Integer, nullable=False)
    row = Column(Integer, nullable=False)
    column = Column(Integer, nullable=False)
    rowspan = Column(Integer, default=1)
    columnspan = Column(Integer, default=1)


class Actionparameter(Base):
    __tablename__ = "actionparameter"

    actionparametercode = Column(Integer, primary_key=True)
    parameterorder = Column(Integer)
    parametervalue = Column(Text)
    cmactioncode = Column(Integer, ForeignKey("cmaction.cmactioncode"), nullable=False)
    parametername = Column(String(255))


class Remaindraftbeer(Base):
    __tablename__ = "remaindraftbeer"

    markingcode = Column(String(255), nullable=False, primary_key=True)
    barcode = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    connectdate = Column(DateTime, nullable=False)
    expirationdate = Column(DateTime)
    volume = Column(Numeric(13, 3), nullable=False)


class TMC(Base):
    __tablename__ = "tmc"
    bcode = Column(String(20), primary_key=True)
    vatcode1 = Column(Integer, default=301)
    vatcode2 = Column(Integer)
    vatcode3 = Column(Integer)
    vatcode4 = Column(Integer)
    vatcode5 = Column(Integer)
    dcode = Column(Integer)
    name = Column(String(200))
    articul = Column(String(200))
    cquant = Column(DECIMAL(13, 3))
    measure = Column(Integer)
    pricetype = Column(Integer)
    price = Column(DECIMAL(13, 2))
    minprice = Column(DECIMAL(13, 2))
    valcode = Column(Integer)
    quantdefault = Column(DECIMAL(13, 3), default=1.000)
    quantlimit = Column(DECIMAL(13, 3))
    ostat = Column(Integer)
    links = Column(Integer)
    quant_mode = Column(Integer, default=15)
    bcode_mode = Column(Integer, default=3)
    op_mode = Column(Integer)
    dept_mode = Column(Integer, default=1)
    price_mode = Column(Integer, default=1)
    tara_flag = Column(Integer)
    tara_mode = Column(Integer)
    tara_default = Column(String(20))
    unit_weight = Column(DECIMAL(13, 3))
    code = Column(String(100))
    aspectschemecode = Column(Integer)
    aspectvaluesetcode = Column(Integer)
    aspectusecase = Column(Integer)
    aspectselectionrule = Column(Integer)
    extendetoptions = Column(String)
    groupcode = Column(String(100))
    remain = Column(DECIMAL(13, 3))
    remaindate = Column(
        String, default="2022-12-22 22:22:22"
    )  # datetime can be used with the correct format
    documentquantlimit = Column(DECIMAL(13, 3))
    age = Column(Integer)
    alcoholpercent = Column(DECIMAL(4, 2))
    inn = Column(String(20))
    kpp = Column(String(20))
    alctypecode = Column(Integer)
    manufacturercountrycode = Column(Integer)
    paymentobject = Column(Integer)
    loyaltymode = Column(Integer, default=0)
    minretailprice = Column(DECIMAL(13, 2))
    ntin = Column(String(255))
    packagecode = Column(String(255))
    ownertype = Column(Integer)


class BARCODES(Base):
    __tablename__ = "barcodes"
    code = Column(String(100), primary_key=True)
    barcode = Column(String(100), primary_key=True)
    name = Column(String(200))
    price = Column(DECIMAL(15, 2))
    cquant = Column(DECIMAL(13, 3))
    measure = Column(Integer)
    aspectvaluesetcode = Column(Integer)
    quantdefault = Column(DECIMAL(13, 3), default=1.000)
    packingmeasure = Column(Integer)
    packingprice = Column(DECIMAL(15, 2))
    minprice = Column(DECIMAL(13, 2))
    minretailprice = Column(DECIMAL(13, 2))
    customsdeclarationnumber = Column(String(32))
    tmctype = Column(Integer)
    ntin = Column(String(255))
    packagecode = Column(String(255))


class Units(Base):
    __tablename__ = "units"
    code = Column(Integer, primary_key=True)
    name = Column(String(255))
    flag = Column(Integer)
    frunit = Column(Integer)


class MOL(Base):
    __tablename__ = "mol"

    code = Column(
        String(30), nullable=False, comment="Код пользователя", primary_key=True
    )  # Обязательно для заполнения
    login = Column(
        String(60), nullable=False, comment="Логин пользователя"
    )  # Обязательно для заполнения
    loginmode = Column(
        Integer, default=0, comment="Зарезервировано для будущего использования"
    )
    name = Column(String(100), comment="Имя пользователя")
    password = Column(String(60), comment="Пароль пользователя")
    locked = Column(
        Integer,
        default=0,
        comment="Запрещена авторизация пользователя (только подтверждение операций): 0 – нет, 1 – да.",
    )
    usergroup = Column(
        Integer, default=0, comment="Зарезервировано для будущего использования"
    )
    drawer = Column(
        Integer, default=0, comment="Зарезервировано для будущего использования"
    )
    start = Column(String(8), comment="Зарезервировано для будущего использования")
    keyposition = Column(
        Integer,
        comment="Порядковый номер положения клавиатурного ключа для подтверждения прав у пользователя",
    )
    rank = Column(String(30), comment="Должность пользователя")
    inn = Column(String(20), comment="ИНН пользователя")


class RoleUser(Base):
    __tablename__ = "roleuser"
    id = Column(Integer, primary_key=True)
    usercode = Column(String(30), nullable=False, comment="Код пользователя")
    rolecode = Column(Integer, default=4, nullable=False, comment="Код роли")
    rule = Column(
        Integer, default=1, nullable=False, comment="Разрешить: 0 - нет, 1 - да"
    )


class Valut(Base):
    __tablename__ = "valut"

    code = Column(Integer, nullable=False, primary_key=True, autoincrement=True)
    stat = Column(Integer, default=0, nullable=False)
    chr = Column(String(4))
    name = Column(String(32))
    type = Column(String(1))
    rate = Column(DECIMAL(13, 4))
    ratecb = Column(DECIMAL(13, 4))
    decpoint = Column(Integer, default=-2)
    round = Column(Integer, default=1)
    mode = Column(Integer)
    drawer = Column(Integer, default=0)
    discascheme = Column(Integer)
    ishidden = Column(Integer, default=0)
    operation = Column(Integer)
    payprocmodule = Column(String(4096))
    merchantid = Column(Integer)
    payprocdir = Column(Text)


class Excisemarkwhite(Base):
    __tablename__ = "excisemarkwhite"

    excisemarkid = Column(
        String(255), primary_key=True, nullable=False, comment="Акцизная марка"
    )
    barcode = Column(String(100), nullable=False, comment="Штрих-код акцизного товара")
    shopcode = Column(String(30), comment="Код магазина")
    excisetype = Column(
        Enum(ExciseTypeEnum),
        default=ExciseTypeEnum.ALCOHOL,
        nullable=False,
        comment="Тип акцизной марки",
    )
    serialnumber = Column(String(255), comment="Серийный номер акцизной марки")
