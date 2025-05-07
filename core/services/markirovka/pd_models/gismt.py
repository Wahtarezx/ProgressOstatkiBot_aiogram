from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from core.services.edo.schemas.login.models import EnumEdoProvider
from core.services.markirovka.enums import (
    GroupIds,
    GisMtDocStatus,
    GisMtDocType,
    GisMtTaskAvailableStatus,
    TaskDownloadeStatus,
    TaskCreateStatus,
    TaskCreatePeriod,
    TaskCreatePeriodicity,
    StatusUOT,
    TypesOrganizations,
)


class Participants(BaseModel):
    inn: str = Field("", title="ИНН участника оборота товаров")
    name: str = Field("", title="Наименование участника оборота товаров")
    statusInn: StatusUOT = Field(
        StatusUOT.NOT_REGISTERED, title="Статус регистрации участника оборота товаров"
    )
    status: str = Field("", title="Текущий статус участника оборота товаров")
    chief: List[str] = Field([], title="Список Ф.И.О. руководителей")
    role: List[TypesOrganizations] = Field(
        [TypesOrganizations.TRADE_PARTICIPANT],
        title="Список кодов типов организации участника оборота товаров",
    )
    is_registered: bool = Field(False, title="Признак регистрации в ГИС МТ")
    is_kfh: bool = Field(
        False,
        title="Признак того, что участник оборота товаров является крестьянским фермерским хозяйством",
    )
    okopf: str = Field("", title="ОКОПФ")
    productGroups: List[str] = Field([], title="Список кодов групп продуктов")


class EdoOperator(BaseModel):
    edo_operator_id: int = Field(0, alias="edoOperatorId")
    edo_operator_name: str = Field("", alias="edoOperatorName")
    participant_edo_id: str = Field("", alias="participantEdoId")
    is_main_operator: bool = Field(False, alias="isMainOperator")
    prefix_edo: str = Field("", alias="prefixEdo")
    hub: bool = Field(False, alias="hub")
    inviting_status: str = Field("", alias="invitingStatus")
    edo_use_hub: bool = Field(False, alias="edoUseHub")
    has_invites: bool = Field(False, alias="hasInvites")


class ProfileEdoInfo(BaseModel):
    participant_id: int = Field(0, alias="participantId")
    org_name: str = Field("", alias="orgName")
    inn: str = Field("", alias="inn")
    kpp: str = Field("", alias="kpp")
    kpp_elk: str = Field("", alias="kppElk")
    ogrn: str = Field("", alias="ogrn")
    first_name: str = Field("", alias="firstName")
    last_name: str = Field("", alias="lastName")
    middle_name: str = Field("", alias="middleName")
    phone: str = Field("", alias="phone")
    edo_operators: List[EdoOperator] = Field("", alias="edoOperators")

    async def get_main_edo_provider(self) -> EdoOperator:
        for edop in self.edo_operators:
            if edop.is_main_operator:
                return edop

    async def check_connect_edo_provider(self, edoprovider_id: int) -> bool:
        for edop in self.edo_operators:
            if edop.edo_operator_id == edoprovider_id:
                return True
        return False

    async def get_providers_may_connect(self) -> list[EdoOperator]:
        return [
            e
            for e in self.edo_operators
            if e.edo_operator_id in [_.value for _ in EnumEdoProvider]
        ]


class ProductRouteGtin(BaseModel):
    data: str = Field("", title="Код Товара")
    group_id: GroupIds = Field(0, title="ID Товарной группы", alias="tg-id")
    error_code: str = Field("", title="Код ошибки", alias="error-code")
    error_msg: str = Field("", title="Сообщение об ошибке", alias="error-msg")


class ProductRouteGtinResponse(BaseModel):
    result: List[ProductRouteGtin] = Field([], title="Результат")


class Exporter(BaseModel):
    exporterName: str = Field("", title="Наименование")
    exporterTaxpayerId: str = Field(
        "", title="ИНН или его аналог (налоговый идентификатор) заявителя"
    )
    kpp: str = Field("", title="КПП или его аналог")
    gcp: str = Field("", title="Глобальный идентификатор компании в GS1")
    gln: str = Field("", title="Глобальный идентификатор места нахождения")
    manufactureAddress: str = Field("", title="Адрес производственной площадки")


class ForeignProducer(BaseModel):
    name: str = Field("", title="Наименование")
    inn: str = Field("", title="ИНН или его аналог (налоговый идентификатор) заявителя")
    kpp: str = Field("", title="КПП или его аналог")
    gcp: str = Field("", title="GCP производителя")
    gln: str = Field("", title="Gln производителя")
    address: list[str] = Field("", title="Массив адрессов производителя")


class Product(BaseModel):
    name: str = Field("", title="Наименование")
    gtin: str = Field("", title="GTIN")
    brand: str = Field("", title="Бренд")
    packageType: str = Field("", title="Тип упаковки")
    innerUnitCount: int = Field(0, title="Количество товара в упаковке")
    model: str = Field("", title="Модель / артикул производителя")
    inn: str = Field("", title="ИНН владельца кода товара (GTIN)")
    exporter: Exporter = Field(
        Exporter(), title="Заявитель маркируемого и вводимого в оборот товара"
    )
    permittedInns: List[str] = Field([], title="Разрешенные ИНН")
    productGroupId: GroupIds = Field(0, title="ID Товарной группы")
    goodSignedFlag: bool = Field(
        False, title="Признак подписания карточки товара в НКМТ"
    )
    goodMarkFlag: bool = Field(False, title="Признак готовности к маркировке")
    goodTurnFlag: bool = Field(False, title="Признак готовности к обороту")
    isKit: bool = Field(False, title="Признак «Комплект» в карточке товара в НКМТ")
    isTechGtin: bool = Field(
        False, title="Признак «Технологический» в карточке товара в НКМТ"
    )
    explain: str = Field(
        "", title="Ошибка заполнения атрибутов и подписания карточки товара в НКМТ"
    )
    foreignProducers: ForeignProducer = Field(
        ForeignProducer(), title="Объект с данными о производителе"
    )
    basicUnit: str = Field("", title="Базовая единица измерения")
    fullName: str = Field("", title="Полное наименование")
    isVarQuantity: bool = Field(False, title="Признак переменного веса")
    volumeWeight: str = Field("", title="Заявленный объём / вес нетто")
    weightMin: str = Field("", title="Диапазон веса, от")
    weightMax: str = Field("", title="Диапазон веса, до")
    coreVolume: int = Field(0, title="Вычисленный объём продукта в мл")
    coreWeight: int = Field(0, title="Вычисленный вес (средний вес) продукта в граммах")
    volumeTradeUnit: str = Field("", title="Объём потребительской единицы")
    expireDuration: str = Field("", title="Срок годности")


class ProductInfo(BaseModel):
    results: List[Product]
    total: int = Field(0, title="Количество найденных товаров")
    errorCode: str = Field("", title="Код ошибки")

    async def product_by_gtin(self, gtin: str) -> Optional[Product]:
        for product in self.results:
            if product.gtin == gtin:
                return product

    @model_validator(mode="after")
    def check_errors(self):
        if self.errorCode:
            raise ValueError(self.errorCode)


class Balance(BaseModel):
    gtin: str = Field("", title="GTIN")
    saldo: int = Field(
        0, title="Начальное сальдо единиц товара на балансе на начало периода"
    )
    actualInput: int = Field(
        0, title="Количество поступивших на баланс единиц товара за текущий день"
    )
    actualOutput: int = Field(
        0, title="Количество убывших с баланса единиц товара за текущий день"
    )
    quantity: int = Field(
        0,
        title="Суммарное количество единиц товара с учётом текущего дня (на 23:59:59 текущего дня)",
    )
    netWeight: int = Field(
        0, title="Суммарный вес товара на балансе на текущую дату, в граммах"
    )
    volume: int = Field(
        0, title="Суммарный объём товара на балансе на текущую дату в миллилитрах"
    )
    actualOperationsCount: int = Field(
        0, title="Число документов по коду товара за текущую дату "
    )


class ActualBalance(BaseModel):
    code: int = Field(0, title="Код ошибки")
    description: str = Field("", title="Описание ошибки")
    balances: List[Balance] = Field(
        [], title="Актуальный баланс по каждому коду товара"
    )

    async def get_all_gtins(self) -> List[str]:
        return [balance.gtin for balance in self.balances]

    @model_validator(mode="after")
    def check_errors(self):
        if self.code != 0:
            raise ValueError(self.description)
        return self


class FileParts(BaseModel):
    id: str = Field("", title="Идентификатор части")
    archivePartSize: int = Field(0, title="Размер части архива")
    fileNumber: int = Field(0, title="Номер части")


class Task(BaseModel):
    id: str = Field(..., title="Идентификатор задачи")
    archiveSize: int = Field(0, title="Размер архива")
    available: GisMtTaskAvailableStatus = Field(
        GisMtTaskAvailableStatus.NOT_AVAILABLE, title="Статус задачи"
    )
    dataStartDate: datetime = Field(
        default_factory=datetime.now, title="Дата начала данных"
    )
    dataEndDate: datetime = Field(
        default_factory=datetime.now, title="Дата окончания данных"
    )
    downloadStatus: TaskDownloadeStatus = Field(
        TaskDownloadeStatus.PREPARATION, title="Статус задачи"
    )
    downloadingTime: int = Field(0, title="Время скачивания")
    downloadFormat: str = Field("", title="Формат скачивания")
    errorMessage: str = Field("", title="Сообщение об ошибке")
    fullErrorMessage: str = Field("", title="Полное сообщение об ошибке")
    fileDeleteDate: datetime = Field(
        default_factory=datetime.now, title="Дата удаления файла"
    )
    generationStartDate: datetime = Field(
        default_factory=datetime.now, title="Дата начала генерации"
    )
    generationEndDate: datetime = Field(
        default_factory=datetime.now, title="Дата окончания генерации"
    )
    notEditable: bool = Field(True, title="Признак невозможности редактирования")
    taskId: str = Field("", title="Идентификатор задачи")
    resultFilePartsSize: int = Field(0, title="Размер частей результата")
    resultFileParts: list[FileParts] = Field([], title="Массив частей результата")


class CreateTask(BaseModel):
    createDate: datetime = Field(
        default_factory=datetime.now, title="Дата создания задачи"
    )
    id: str = Field(..., title="Идентификатор задачи")
    name: str = Field("", title="Название задачи")
    currentStatus: TaskCreateStatus = Field(
        TaskCreateStatus.PREPARATION, title="Статус задачи"
    )
    dataStartDate: datetime = Field(
        default_factory=datetime.now, title="Дата начала данных"
    )
    dataEndDate: datetime = Field(
        default_factory=datetime.now, title="Дата окончания данных"
    )
    orgInn: str = Field("", title="ИНН организации")
    period: TaskCreatePeriod = Field(
        TaskCreatePeriod.QUARTER, title="Периодичность регулярной выгрузки"
    )
    periodicity: TaskCreatePeriodicity = Field(
        TaskCreatePeriodicity.SINGLE, title="Вид периодичности выгрузки"
    )
    productGroupCode: GroupIds = Field(0, title="Товарная группа")
    timeoutSecs: int = Field(0, title="Таймаут задачи")


class TaskInfoProductGroups(BaseModel):
    id: int = Field(0, title="Идентификатор текущей задачи")
    name: str = Field("", title="Наименование товарной группы")


class TaskInfo(BaseModel):
    id: str = Field(..., title="Идентификатор задачи")
    name: str = Field("", title="Название задачи")
    createDate: datetime = Field(
        default_factory=datetime.now, title="Дата создания задачи"
    )
    currentStatus: TaskCreateStatus = Field("", title="Статус задачи")
    orgInn: str = Field("", title="ИНН организации")
    productGroupCode: GroupIds = Field(0, title="Товарная группа")
    downloadingStorageDays: int = Field(0, title="Срок хранения данных")
    productGroups: List[TaskInfoProductGroups] = Field(
        [], title="Доступные товарные группы для текущего типа задач"
    )
    timeoutSecs: int = Field(0, title="Таймаут задачи")


class DispensersResults(BaseModel):
    list: list[Task]


class GisMtProductInfo(BaseModel):
    name: str = ""
    gtin: str = ""
    productGroup: str = ""
    productGroupId: GroupIds = Field(0, title="ID Товарной группы")
    coreVolume: int = 0
    shelfLifeSpecializedPackageDays: int | None = Field(
        None, title="Срок годности в днях после вскрытия специализированной упаковки"
    )


class ProductInfoResponse(BaseModel):
    results: list[GisMtProductInfo]
    total: int


class Code(BaseModel):
    cis: str = Field(..., title="КИ / КиЗ")
    valid: bool = Field(False, title="Результат проверки валидности структуры КИ / КиЗ")
    printView: str = Field("", title="КИ без криптоподписи / КиЗ")
    gtin: str = Field("", title="Код товара")
    groupIds: List[GroupIds] = Field([0], title="Массив идентификаторов товарных групп")
    verified: bool = Field(False, title="Результат проверки криптоподписи КИ")
    realizable: bool = Field(True, title="Признак возможности реализации КИ / КиЗ")
    utilised: bool = Field(True, title="Признак нанесения КИ / КиЗ на упаковку")
    expireDate: Optional[str] = Field("", title="Дата истечения срока годности")
    productionDate: Optional[str] = Field("", title="Дата производства продукции")
    prVetDocument: Optional[str] = Field(
        "", title="Производственный ветеринарный сопроводительный документ"
    )
    isOwner: bool = Field(False, title="Признак владения кодом")
    errorCode: int = Field(0, title="Код ошибки")
    isTracking: bool = Field(
        True, title="Признак старта прослеживаемости в товарной группе"
    )
    sold: bool = Field(True, title="Признак продажи товара")
    packageType: str = Field("", title="Тип упаковки")
    producerInn: str = Field("", title="ИНН производителя")
    found: bool = Field(True, title="Признак наличия КМ в ГИС МТ")
    innerUnitCount: int = Field(0, title="Объем. Пиво в мл, Молочка в г")
    soldUnitCount: int = Field(0, title="Количество проданных единиц товара")

    @field_validator("valid")
    def check_valid(cls, v):
        if not v:
            return ValueError(f"Отправленный код не является маркировкой")

    @field_validator("errorCode")
    def error_check(cls, errorCode: int):
        if errorCode == 0:
            return
        elif errorCode == 1:
            raise ValueError(f"Ошибка валидации КМ")
        elif errorCode == 2:
            raise ValueError(f"КМ не содержит GTIN")
        elif errorCode == 3:
            raise ValueError(f"КМ не содержит серийный номер")
        elif errorCode == 4:
            raise ValueError(f"КМ содержит недопустимые символы")
        elif errorCode == 5:
            raise ValueError(
                f"Ошибка верификации криптоподписи КМ (формат крипто-подписи не соответствует типу КМ)"
            )
        elif errorCode == 6:
            raise ValueError(
                f"Ошибка верификации криптоподписи КМ (крипто-подпись не валидная)"
            )
        elif errorCode == 7:
            raise ValueError(
                f"Ошибка верификации криптоподписи КМ (крипто-ключ не валиден)"
            )
        elif errorCode == 8:
            raise ValueError(f"КМ не прошел верификацию в стране эмитента")
        elif errorCode == 9:
            raise ValueError(f"Найденные AI в КМ не поддерживаются")
        elif errorCode == 10:
            raise ValueError(f"КМ не найден в ГИС МТ")


class CodeResponse(BaseModel):
    code: int = Field(0, title="Результат обработки операции")
    description: str = Field(
        "", title="Текстовое описание результата выполнения метода"
    )
    codes: Optional[List[Code]] = Field([], title="Список КИ / КиЗ")
    reqId: str = Field("", title="Уникальный идентификатор запроса")
    reqTimestamp: int = Field("", title="Дата и время формирования запроса")

    @model_validator(mode="after")
    def check_valid(self):
        if self.code == 410:
            raise ValueError("Отсканируйте маркировку товара")
        elif self.code != 0:
            raise ValueError(self.model_dump_json())
        return self


class MOD(BaseModel):
    address: str = Field(title="Адрес", default="")
    kpp: str = Field(title="КПП", default="")
    fiasId: str = Field(title="ФИАС ID", default="")
    isBlockedEgais: bool = Field(title="Признак блокировки МОД в ЕГАИС", default=False)


class MODS(BaseModel):
    result: List[MOD] = Field(title="МОД", default=[])
    total: int = Field(title="Всего", default=0)
    nextPage: bool = Field(title="Следующая страница", default=False)

    def delete_empty_fias(self) -> None:
        self.result = [mod for mod in self.result if mod.fiasId]

    async def get_mod_by_fias(self, fias: str) -> MOD:
        for mod in self.result:
            if mod.fiasId == fias:
                return mod

    async def get_mod_by_kpp(self, kpp: str) -> MOD:
        for mod in self.result:
            if mod.kpp == kpp:
                return mod

    async def get_mod_by_address(self, address: str) -> MOD:
        for mod in self.result:
            if mod.address == address:
                return mod

    async def text_inline(self) -> str:
        mods_text = "Выберите МОД\n\n"
        for i, mod in enumerate(self.result, start=1):
            mods_text += f"{i}. <b>{mod.address}</b>\n"
            mods_text += "➖➖➖➖➖➖\n"
        return mods_text


class DocInfo(BaseModel):
    error_message: str = Field(title="Ошибка", default="")
    number: str = Field(title="Тип документа", default="")
    docDate: str = Field(title="Дата документа", default="")
    receivedAt: str = Field(title="Дата документа", default="")
    type: GisMtDocType = Field(title="Тип документа", default=GisMtDocType.CONNECT_TAP)
    status: GisMtDocStatus = Field(
        title="Статус документа", default=GisMtDocStatus.CHECKED_NOT_OK
    )
    senderInn: str = Field(title="ИНН отправителя", default="")
    senderName: str = Field(title="Имя отправителя", default="")
    downloadStatus: GisMtDocStatus = Field(
        title="Статус документа", default=GisMtDocStatus.CHECKED_NOT_OK
    )
    downloadDesc: str = Field(title="Пишет ошибку если нельзя скачать", default="")
    content: str = Field(title="Отправленная информация", default="")
    productGroupId: List[GroupIds] = Field(title="ID товарной группы", default=[0])
    errors: Optional[list] = Field(title="Список ошибок", default=[])

    def get_name_response(self) -> str:
        statuses = {
            GisMtDocStatus.IN_PROGRESS.value: "Проверяется",
            GisMtDocStatus.CHECKED_OK.value: "Обработан",
            GisMtDocStatus.CHECKED_NOT_OK.value: "Обработан с ошибками",
            GisMtDocStatus.PROCESSING_ERROR.value: "Техническая ошибка",
            GisMtDocStatus.PARSE_ERROR.value: "Обработан с ошибками",
            GisMtDocStatus.WAIT_FOR_CONTINUATION.value: "Проверяется",
            GisMtDocStatus.ACCEPTED.value: "Принят",
            GisMtDocStatus.CANCELLED.value: "Аннулирован",
            GisMtDocStatus.WAIT_ACCEPTANCE.value: "Ожидает приёмку",
            GisMtDocStatus.WAIT_PARTICIPANT_REGISTRATION.value: "Ожидает регистрации участника в ГИС МТ",
        }
        return statuses.get(self.status.value, "Неизвестный ответ")

    def gisMt_error_response(self) -> bool:
        if (
            self.status == GisMtDocStatus.CHECKED_NOT_OK
            or self.status == GisMtDocStatus.PROCESSING_ERROR
            or self.status == GisMtDocStatus.PARSE_ERROR
        ):
            return False
        return True

    def wait_response(self) -> bool:
        if self.error_message:
            if "Документ не найден в ГИС МТ".lower() in self.error_message.lower():
                return False
            raise ValueError(self.error_message)
        if self.status in [
            GisMtDocStatus.IN_PROGRESS,
            GisMtDocStatus.WAIT_FOR_CONTINUATION,
        ]:
            return False
        return True


class CisInfoExpirations(BaseModel):
    expirationStorageDate: datetime | None = None
    storageConditionId: int | None = None
    storageConditionName: str | None = None


class CisInfo(BaseModel):
    applicationDate: datetime | None = None
    introducedDate: datetime | None = None
    kpp: str | None = None
    requestedCis: str | None = None
    cis: str | None = None
    gtin: str | None = None
    tnVedEaes: str | None = None
    tnVedEaesGroup: str | None = None
    productName: str | None = None
    productGroupId: GroupIds | None = None
    productGroup: str | None = None
    brand: str | None = None
    producedDate: datetime | None = None
    emissionDate: datetime | None = None
    emissionType: str | None = None
    packageType: str | None = None
    generalPackageType: str | None = None
    ownerInn: str | None = None
    ownerName: str | None = None
    status: str | None = None
    statusEx: str | None = None
    producerInn: str | None = None
    producerName: str | None = None
    markWithdraw: bool | None = None
    expirationDate: datetime | None = None
    volumeSpecialPack: str | None = None


class CisesInfoResponse(BaseModel):
    cisInfo: CisInfo


if __name__ == "__main__":
    balance = '{"code":0,"description":"Ok","balances":[{"gtin":"00000046062796","saldo":-44,"actualInput":0,"actualOutput":-10,"quantity":-54,"netWeight":-4320,"volume":0,"actualOperationsCount":1},{"gtin":"04607030633596","saldo":-136,"actualInput":0,"actualOutput":-4,"quantity":-140,"netWeight":-9800,"volume":0,"actualOperationsCount":1},{"gtin":"04607030633718","saldo":-21,"actualInput":0,"actualOutput":0,"quantity":-21,"netWeight":-1470,"volume":0,"actualOperationsCount":0},{"gtin":"04607030634388","saldo":-29,"actualInput":0,"actualOutput":0,"quantity":-29,"netWeight":-2320,"volume":0,"actualOperationsCount":0},{"gtin":"04607030634517","saldo":-2,"actualInput":0,"actualOutput":-1,"quantity":-3,"netWeight":-1350,"volume":0,"actualOperationsCount":1},{"gtin":"04607030634531","saldo":-1,"actualInput":0,"actualOutput":0,"quantity":-1,"netWeight":-80,"volume":0,"actualOperationsCount":0},{"gtin":"04607030636665","saldo":-27,"actualInput":0,"actualOutput":0,"quantity":-27,"netWeight":-2970,"volume":0,"actualOperationsCount":0},{"gtin":"04607030636900","saldo":-13,"actualInput":0,"actualOutput":0,"quantity":-13,"netWeight":-1430,"volume":0,"actualOperationsCount":0},{"gtin":"04607031701614","saldo":49,"actualInput":0,"actualOutput":0,"quantity":49,"netWeight":0,"volume":24500,"actualOperationsCount":0},{"gtin":"04607031701621","saldo":49,"actualInput":0,"actualOutput":0,"quantity":49,"netWeight":0,"volume":73500,"actualOperationsCount":0},{"gtin":"04607031701904","saldo":61,"actualInput":0,"actualOutput":-1,"quantity":60,"netWeight":0,"volume":30000,"actualOperationsCount":1},{"gtin":"04607031701911","saldo":24,"actualInput":0,"actualOutput":0,"quantity":24,"netWeight":0,"volume":36000,"actualOperationsCount":0},{"gtin":"04630012980982","saldo":-55,"actualInput":0,"actualOutput":-2,"quantity":-57,"netWeight":-3990,"volume":0,"actualOperationsCount":1},{"gtin":"04630012981057","saldo":-113,"actualInput":0,"actualOutput":0,"quantity":-113,"netWeight":-10170,"volume":0,"actualOperationsCount":0},{"gtin":"0463012981323","saldo":-71,"actualInput":0,"actualOutput":0,"quantity":-71,"netWeight":-4970,"volume":0,"actualOperationsCount":0},{"gtin":"04630012981330","saldo":-23,"actualInput":0,"actualOutput":0,"quantity":-23,"netWeight":-2070,"volume":0,"actualOperationsCount":0},{"gtin":"04630012981347","saldo":-1,"actualInput":0,"actualOutput":0,"quantity":-1,"netWeight":-110,"volume":0,"actualOperationsCount":0},{"gtin":"04630012981378","saldo":-29,"actualInput":0,"actualOutput":0,"quantity":-29,"netWeight":-2320,"volume":0,"actualOperationsCount":0},{"gtin":"04630012981446","saldo":-63,"actualInput":0,"actualOutput":0,"quantity":-63,"netWeight":-4410,"volume":0,"actualOperationsCount":0},{"gtin":"04630012981507","saldo":-31,"actualInput":0,"actualOutput":0,"quantity":-31,"netWeight":-2170,"volume":0,"actualOperationsCount":0},{"gtin":"04630012981538","saldo":-88,"actualInput":0,"actualOutput":0,"quantity":-88,"netWeight":-5720,"volume":0,"actualOperationsCount":0},{"gtin":"04630012982214","saldo":-48,"actualInput":0,"actualOutput":0,"quantity":-48,"netWeight":-3840,"volume":0,"actualOperationsCount":0},{"gtin":"04630012982788","saldo":-26,"actualInput":0,"actualOutput":0,"quantity":-26,"netWeight":-2080,"volume":0,"actualOperationsCount":0},{"gtin":"04630012983594","saldo":-39,"actualInput":0,"actualOutput":0,"quantity":-39,"netWeight":-3120,"volume":0,"actualOperationsCount":0},{"gtin":"04630012983778","saldo":-110,"actualInput":0,"actualOutput":-2,"quantity":-112,"netWeight":-7280,"volume":0,"actualOperationsCount":1},{"gtin":"04640043910339","saldo":-5,"actualInput":0,"actualOutput":0,"quantity":-5,"netWeight":-400,"volume":0,"actualOperationsCount":0},{"gtin":"04640043910346","saldo":-2,"actualInput":0,"actualOutput":0,"quantity":-2,"netWeight":-160,"volume":0,"actualOperationsCount":0},{"gtin":"04640043910391","saldo":-2,"actualInput":0,"actualOutput":0,"quantity":-2,"netWeight":-160,"volume":0,"actualOperationsCount":0},{"gtin":"04640043910575","saldo":-1,"actualInput":0,"actualOutput":0,"quantity":-1,"netWeight":-80,"volume":0,"actualOperationsCount":0}]}'

    print(ActualBalance.model_validate_json(balance))
