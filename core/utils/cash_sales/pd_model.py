from datetime import datetime, date
from typing import List, Optional, Any

from pydantic import BaseModel


class Tax(BaseModel):
    taxCode: Optional[int]
    taxRate: Optional[float]
    taxSum: Optional[float]


class InventPosition(BaseModel):
    accountingQuant: Optional[float]
    additionalbarcode: Optional[str]
    additionaldata: Optional[str]
    additionalexcisemark: Optional[Any]
    alcocode: Optional[str]
    alcoholPercent: Optional[float]
    alcosetPositions: List[Any]
    alctypecode: Optional[int]
    articul: Optional[str]
    aspectPosition: List[Any]
    aspectschemecode: Optional[Any]
    aspectvaluesetcode: Optional[Any]
    barCode: Optional[str]
    baseSum: Optional[float]
    bcodeMode: Optional[str]
    bcode_main: Optional[str]
    bonusPositions: List[Any]
    buttonid: Optional[Any]
    c_link: Optional[int]
    cashcode: Optional[str]
    checkmarkresult: Optional[Any]
    consultant: Optional[Any]
    consultantid: Optional[Any]
    customsdeclarationnumber: Optional[Any]
    departmentid: Optional[Any]
    deptCode: Optional[int]
    disc_abs: Optional[float]
    disc_perc: Optional[float]
    discountPositions: List[Any]
    docnum: Optional[str]
    dopdata: Optional[int]
    excisemark: Optional[str]
    excisetype: Optional[str]
    extdocid: Optional[str]
    extendetoptions: Optional[Any]
    finalPrice: Optional[float]
    frnum: Optional[int]
    gift: Optional[Any]
    inn: Optional[Any]
    inventCode: Optional[str]
    kpp: Optional[Any]
    manufacturercountrycode: Optional[Any]
    measureCode: Optional[int]
    medicine: Optional[Any]
    minPrice: Optional[float]
    minretailprice: Optional[float]
    modSum: Optional[float]
    name: Optional[str]
    ntin: Optional[Any]
    opCode: Optional[int]
    opid: Optional[Any]
    ost_modif: Optional[int]
    packingprice: Optional[float]
    paymentitemid: Optional[Any]
    paymentmethod: Optional[int]
    paymentobject: Optional[int]
    posNum: Optional[int]
    posSum: Optional[float]
    posTime: Optional[datetime]
    prepackaged: Optional[int]
    price: Optional[float]
    priceIndex: Optional[int]
    priceMode: Optional[int]
    priceType: Optional[int]
    pricedoctype: Optional[Any]
    pricevcode: Optional[int]
    quant: Optional[float]
    quantMode: Optional[str]
    status: Optional[int]
    sume: Optional[float]
    supplier: Optional[Any]
    tags: Optional[str]
    taracapacity: Optional[float]
    taramode: Optional[int]
    taxes: List[Tax]
    userCode: Optional[str]
    vatcode1: Optional[int]
    vatcode2: Optional[int]
    vatcode3: Optional[int]
    vatcode4: Optional[int]
    vatcode5: Optional[int]
    vatrate1: Optional[float]
    vatrate2: Optional[float]
    vatrate3: Optional[float]
    vatrate4: Optional[float]
    vatrate5: Optional[float]
    vatsum1: Optional[float]
    vatsum2: Optional[float]
    vatsum3: Optional[float]
    vatsum4: Optional[float]
    vatsum5: Optional[float]


class MoneyPosition(BaseModel):
    acode: Optional[str]
    authcode: Optional[Any]
    balance: Optional[float]
    bond: Optional[float]
    bond_quant: Optional[int]
    c_link: Optional[int]
    cardnum: Optional[str]
    cashcode: Optional[str]
    discnumber: Optional[int]
    docnum: Optional[str]
    dopdata: Optional[int]
    endcardnum: Optional[str]
    frnum: Optional[int]
    merchantid: Optional[Any]
    nrate: Optional[float]
    opCode: Optional[int]
    operationId: Optional[Any]
    paymentmethod: Optional[int]
    posTime: Optional[datetime]
    slip: Optional[Any]
    sourceoperationid: Optional[Any]
    sumB: Optional[float]
    sume: Optional[float]
    sumn: Optional[float]
    userCode: Optional[str]
    valCode: Optional[int]
    valName: Optional[str]
    valutOperation: Optional[int]
    vsum: Optional[float]


class Check(BaseModel):
    actorCode: Optional[Any]
    backReason: Optional[Any]
    baseSum: Optional[float]
    bonusPositions: List[Any]
    buttonPositions: List[Any]
    buttonid: Optional[Any]
    c_link: Optional[int]
    cardPositions: List[Any]
    cashCode: Optional[str]
    certificatePositions: List[Any]
    clientPositions: List[Any]
    clientitemid: Optional[Any]
    closeWithoutPrint: Optional[int]
    closed: Optional[int]
    correctionReason: Optional[Any]
    correctionSourceDocDate: Optional[Any]
    correctionSourceDocNum: Optional[Any]
    correctionType: Optional[Any]
    couponPositions: List[Any]
    customerAddress: Optional[Any]
    dateincrement: Optional[int]
    departmentid: Optional[Any]
    deptCode: Optional[int]
    deptPositions: List[Any]
    digitalSignatureEgais: Optional[str]
    disc_abs: Optional[float]
    disc_perc: Optional[float]
    docNum: Optional[int]
    docSum: Optional[float]
    docType: Optional[int]
    dopdata: Optional[int]
    failedMoneyPositions: List[Any]
    fiscalIdentifier: Optional[Any]
    fiscaldocument: List[Any]
    frDocCopy: Optional[Any]
    frdocnum: Optional[Any]
    giftPositions: List[Any]
    identifier: Optional[str]
    inventPositions: List[InventPosition]
    linkeddocumentid: Optional[Any]
    modSum: Optional[float]
    moneyPositions: List[MoneyPosition]
    moneyouttype: Optional[Any]
    noPdfDigitalSignatureEgais: Optional[Any]
    noPdfUrlEgais: Optional[Any]
    opid: Optional[Any]
    paymentPositions: List[Any]
    rtext: Optional[Any]
    shift: Optional[int]
    shiftType: Optional[int]
    sourceidentifier: Optional[Any]
    stornoPositions: List[Any]
    sum2m: Optional[float]
    sumcash: Optional[float]
    sume: Optional[float]
    summode: Optional[int]
    sumn: Optional[float]
    sumnoncash: Optional[float]
    sumother: Optional[float]
    sumtype: Optional[int]
    timeBeg: Optional[datetime]
    timeEnd: Optional[datetime]
    urlEgais: Optional[str]
    userCode: Optional[str]
    vatsum: Optional[float]
    vbrate: Optional[float]
    verate: Optional[float]
    waybillNumber: Optional[Any]
    waybillPrinted: Optional[Any]


class User(BaseModel):
    rank: Optional[str]
    usercode: Optional[str]
    username: Optional[str]


class KKM(BaseModel):
    countBack: Optional[int]
    countMoneyIn: Optional[int]
    countMoneyOut: Optional[int]
    countSale: Optional[int]
    crashed: Optional[int]
    fnnumber: Optional[str]
    kkmNum: Optional[int]
    modelName: Optional[str]
    modelNum: Optional[int]
    paymentName1: Optional[str]
    paymentName2: Optional[str]
    paymentName3: Optional[str]
    paymentName4: Optional[str]
    paymentName5: Optional[str]
    paymentName6: Optional[str]
    producerCode: Optional[int]
    producerName: Optional[str]
    serialNum: Optional[str]
    shiftnumkkm: Optional[int]
    sumBack: Optional[float]
    sumBackByPayment1: Optional[float]
    sumBackByPayment2: Optional[float]
    sumBackByPayment3: Optional[float]
    sumBackByPayment4: Optional[float]
    sumBackByPayment5: Optional[float]
    sumBackByPayment6: Optional[float]
    sumBackEklz: Optional[float]
    sumCashBeg: Optional[float]
    sumCashEnd: Optional[float]
    sumGain: Optional[float]
    sumMoneyIn: Optional[float]
    sumMoneyOut: Optional[float]
    sumProtectedBeg: Optional[float]
    sumProtectedEnd: Optional[float]
    sumSale: Optional[float]
    sumSaleByPayment1: Optional[float]
    sumSaleByPayment2: Optional[float]
    sumSaleByPayment3: Optional[float]
    sumSaleByPayment4: Optional[float]
    sumSaleByPayment5: Optional[float]
    sumSaleByPayment6: Optional[float]
    sumSaleEklz: Optional[float]
    sumbackdept1: Optional[float]
    sumbackdept2: Optional[float]
    sumbackdept3: Optional[float]
    sumbackdept4: Optional[float]
    sumbackdept5: Optional[float]
    sumbackdept6: Optional[float]
    sumbackdept7: Optional[float]
    sumbackdept8: Optional[float]
    sumbackdept9: Optional[float]
    sumbackdept10: Optional[float]
    sumbackdept11: Optional[float]
    sumbackdept12: Optional[float]
    sumbackdept13: Optional[float]
    sumbackdept14: Optional[float]
    sumbackdept15: Optional[float]
    sumbackdept16: Optional[float]
    sumsaledept1: Optional[float]
    sumsaledept2: Optional[float]
    sumsaledept3: Optional[float]
    sumsaledept4: Optional[float]
    sumsaledept5: Optional[float]
    sumsaledept6: Optional[float]
    sumsaledept7: Optional[float]
    sumsaledept8: Optional[float]
    sumsaledept9: Optional[float]
    sumsaledept10: Optional[float]
    sumsaledept11: Optional[float]
    sumsaledept12: Optional[float]
    sumsaledept13: Optional[float]
    sumsaledept14: Optional[float]
    sumsaledept15: Optional[float]
    sumsaledept16: Optional[float]
    unsenddoccount: Optional[int]
    unsenddocdate: Optional[datetime]


class ShiftInfo(BaseModel):
    cashCode: Optional[str]
    checkNum1: Optional[int]
    checkNum2: Optional[int]
    countrefund: Optional[int]
    countsale: Optional[int]
    firstchecktime: Optional[datetime]
    kkms: List[KKM]
    shift: Optional[int]
    shopcode: Optional[str]
    sumDrawer: Optional[float]
    sumGain: Optional[float]
    sumSale: Optional[float]
    sumgaincash: Optional[float]
    sumgainnoncash: Optional[float]
    sumrefund: Optional[float]
    sumrefundcash: Optional[float]
    sumrefundnoncash: Optional[float]
    sumsalecash: Optional[float]
    sumsalenoncash: Optional[float]
    sumsaleother: Optional[float]
    timeBeg: Optional[datetime]
    timeEnd: Optional[datetime]
    type: Optional[int]
    update_time: Optional[datetime]
    userCode: Optional[str]
    users: List[User]


class Shift(BaseModel):
    checks: list[Check]
    shift: ShiftInfo


class CashShifts(BaseModel):
    shifts: list[Shift]

    async def get_shifts_by_date(self, start_date: date, end_date: date) -> list[Shift]:
        self.shifts = [
            shift
            for shift in self.shifts
            if shift.shift.timeEnd is not None and shift.shift.timeBeg is not None
            if start_date
            <= date(
                shift.shift.timeEnd.year,
                shift.shift.timeEnd.month,
                shift.shift.timeEnd.day,
            )
            < end_date
        ]
        return self
