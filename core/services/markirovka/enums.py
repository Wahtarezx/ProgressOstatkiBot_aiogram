import enum

from pydantic import BaseModel, Field


class TypesOrganizations(enum.Enum):
    """Типы организации"""

    TRADE_PARTICIPANT = "TRADE_PARTICIPANT"  # Участник оборота товаров
    PRODUCER = "PRODUCER"  # Производитель товара
    IMPORTER = "IMPORTER"  # Импортер товара
    WHOLESALER = "WHOLESALER"  # Оптовая торговля
    RETAIL = "RETAIL"  # Розничная торговля
    IS_MP_OPERATOR = "IS_MP_OPERATOR"  # Оператор ГИС МТ
    OGV = "OGV"  # Орган государственной власти
    EMITENT = "EMITENT"  # Эмитент


class StatusUOT(enum.Enum):
    """Статусы УОТ"""

    REGISTERED = "REGISTERED"  # Зарегистрирован
    PRE_REGISTERED = "PRE_REGISTERED"  # Предварительная регистрация началась
    NOT_REGISTERED = "NOT_REGISTERED"  # Не зарегистрирован
    REMOVED = "REMOVED"  # Удален
    RESTORED = "RESTORED"  # Восстановлен
    BLOCKED = "BLOCKED"  # Заблокирован
    PRE_REGISTERED_ISSUER = (
        "PRE_REGISTERED_ISSUER"  # Предварительная регистрация производителя
    )
    PRE_REGISTERED_TRADER = (
        "PRE_REGISTERED_TRADER"  # Предварительная регистрация продавца
    )


class TaskCreateStatus(enum.Enum):
    PREPARATION = "PREPARATION"  # Подготовка
    COMPLETED = "COMPLETED"  # Выполнено
    CANCELED = "CANCELED"  # Отменено
    ARCHIVE = "ARCHIVE"  # Архив
    FAILED = "FAILED"  # Ошибка


class TaskCreatePeriod(enum.Enum):
    """Периодичность регулярной выгрузки"""

    HALF_MIN = "HALF_MIN"  # Полминуты
    TEN_MINUTES = "TEN_MINUTES"  # 10 минут
    DAY = "DAY"  # День
    MONTH = "MONTH"  # Месяц
    QUARTER = "QUARTER"  # Квартал
    YEAR = "YEAR"  # Год


class TaskCreatePeriodicity(enum.Enum):
    """Вид периодичности выгрузки"""

    SINGLE = "SINGLE"  # Однократная
    REGULAR = "REGULAR"  # Регулярная


class TaskDownloadeStatus(enum.Enum):
    SUCCESS = "SUCCESS"  # Успешно
    PREPARATION = "PREPARATION"  # В обработке
    FAILED = "FAILED"  # Неуспешно


class GisMtTaskAvailableStatus(enum.Enum):
    AVAILABLE = "AVAILABLE"  # доступен
    NOT_AVAILABLE = "NOT_AVAILABLE"  # недоступен


class GisMtDocType(enum.Enum):
    LK_RECEIPT = "LK_RECEIPT"  # Вывод из оборота 4.2.8
    LK_GTIN_RECEIPT = "LK_GTIN_RECEIPT"  # Вывод из оборота (ОСУ) 4.2.9
    CONNECT_TAP = "CONNECT_TAP"  # Подключение кега к оборудованию для розлива 4.2.15


class GisMtDocStatus(enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    CHECKED_OK = "CHECKED_OK"
    CHECKED_NOT_OK = "CHECKED_NOT_OK"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    PARSE_ERROR = "PARSE_ERROR"
    WAIT_FOR_CONTINUATION = "WAIT_FOR_CONTINUATION"
    # Следующие только для документа "Отгрузка"
    ACCEPTED = "ACCEPTED"
    CANCELLED = "CANCELLED"
    WAIT_ACCEPTANCE = "WAIT_ACCEPTANCE"
    WAIT_PARTICIPANT_REGISTRATION = "WAIT_PARTICIPANT_REGISTRATION"


class GroupIds(enum.IntEnum):
    unknown = 0  # Неизвестно
    lp = 1  # Предметы одежды, бельё постельное, столовое, туалетное и кухонное
    shoes = 2  # Обувные товары
    tobacco = 3  # Табачная продукция
    perfumery = 4  # Духи и туалетная вода
    tires = 5  # Шины и покрышки пневматические резиновые новые
    electronics = 6  # Фотокамеры (кроме кинокамер) фотовспышки и лампы-вспышки
    milk = 8  # Молочная продукция
    bicycle = 9  # Велосипеды и велосипедные рамы
    wheelchairs = 10  # Медицинские изделия
    otp = 12  # Альтернативная табачная продукция
    water = 13  # Упакованная вода
    furs = 14  # Товары из натурального меха
    beer = 15  # Пиво напитки изготавливаемые на основе пива слабоалкогольные напитки
    ncp = 16  # Никотиносодержащая продукция
    bio = 17  # Биологически активные добавки к пище
    antiseptic = 19  # Антисептики и дезинфицирующие средства
    petfood = 20  # Корма для животных
    seafood = 21  # Морепродукты
    nabeer = 22  # Безалкогольное пиво
    softdrinks = 23  # Соковая продукция и безалкогольные напитки
    vetpharma = 26  # Ветеринарные препараты
    toys = 27  # Игры и игрушки для детей
    radio = 28  # Радиоэлектронная продукция
    titan = 31  # Титановая металлопродукция
    conserve = 32  # Консервированная продукция
    vegetableoil = 33  # Растительные масла
    opticfiber = 34  # Оптоволокно и оптоволоконная продукция
    chemistry = 35  # Парфюмерные и косметические средства и бытовая химия
    pharmaraw = 38  # Фармацевтическое сырьё, лекарственные средства


if __name__ == "__main__":
    print(TaskDownloadeStatus.SUCCESS)
