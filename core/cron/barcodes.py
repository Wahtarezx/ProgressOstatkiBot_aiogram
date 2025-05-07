import asyncio
import os.path
import re
import joblib
from typing import Sequence

from sqlalchemy import text, MetaData, create_engine
from sqlalchemy.orm import *
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from concurrent.futures import ThreadPoolExecutor

from core.database.query_BOT import (
    get_barcodes_for_add,
    update_status_barcode,
    get_unique_cashnumbers_from_barcodes,
    get_barcodes_for_price,
)
from core.database.modelBOT import *
from core.database.query_PROGRESS import get_cash_info
from loguru import logger

from core.loggers.make_loggers import except_log
from core.utils import texts
from core.database.artix.model import TMC


model = joblib.load('core/services/ml/model.pkl')
BATCH_SIZE = 1000
MAX_WORKERS = 80
CHUNK_SIZE = 1000
PARALLEL_BATCHES = 5


async def add_to_autoupdate_ean(barcode, dcode, op_mode, tmctype):
    file_path = os.path.join(config.server_path, "changeProduct", "2.txt")
    # if os.path.exists(file_path):
    #     with open(file_path, 'a') as f:
    #         f.write(f'{barcode}|{dcode}|{op_mode}|{tmctype}\n')


async def add_barcodes_in_cash(ip: str, barcodes_for_add: Sequence):
    engine = create_engine(
        f"mysql+pymysql://{config.cash_user}:{config.cash_password}@{ip}:{config.port}/{config.cash_database}?charset=utf8mb4",
        pool_recycle=3600,
        pool_timeout=30,
    )
    Session = sessionmaker(bind=engine)
    if len(barcodes_for_add) > 0:
        with Session() as s:
            for barcode in barcodes_for_add:
                logger.debug(f"Добавил ШК {barcode.bcode}")
                s.execute(
                    text(f"DELETE FROM tmc WHERE code = '{barcode.bcode}' LIMIT 1")
                )
                s.execute(
                    text(f"DELETE FROM barcodes WHERE code = '{barcode.bcode}' LIMIT 1")
                )
                s.execute(
                    text(
                        "INSERT IGNORE INTO tmc (bcode, vatcode1, vatcode2, vatcode3, vatcode4, vatcode5, dcode, name, articul, cquant, measure, pricetype, price, minprice, valcode, quantdefault, quantlimit, ostat, links, quant_mode, bcode_mode, op_mode, dept_mode, price_mode, tara_flag, tara_mode, tara_default, unit_weight, code, aspectschemecode, aspectvaluesetcode, aspectusecase, aspectselectionrule, extendetoptions, groupcode, remain, remaindate, documentquantlimit, age, alcoholpercent, inn, kpp, alctypecode, manufacturercountrycode, paymentobject, loyaltymode, minretailprice)"
                        "VALUES (:bcode, 301, 302, 303, 304, 305, :dcode, :name, '', 1.000, :measure, 0, :price, 1.00, 0, :qdefault, 0.000, 0, 0, 15, 3, :op_mode, 1, 1, NULL, NULL, '0', NULL, :bcode, NULL, NULL, NULL, NULL, NULL, NULL, 0.000, '2021-22-12 22:22:22', 2.000, NULL, 15.00, NULL, NULL, 0, NULL, NULL, 0, 1.00);"
                    ),
                    {
                        "bcode": barcode.bcode,
                        "dcode": barcode.dcode,
                        "name": barcode.name,
                        "measure": barcode.measure,
                        "price": barcode.price,
                        "op_mode": barcode.op_mode,
                        "qdefault": barcode.qdefault,
                    },
                )

                s.execute(
                    text(
                        "INSERT IGNORE INTO barcodes (code, barcode, name, price, cquant, measure, aspectvaluesetcode, quantdefault, packingmeasure, packingprice, minprice, minretailprice, customsdeclarationnumber, tmctype)"
                        "VALUES (:bcode, :bcode, :name, :price, NULL, :measure, NULL, :qdefault, 2, NULL, 1.00, 1.00, NULL, :tmctype);"
                    ),
                    {
                        "bcode": barcode.bcode,
                        "name": barcode.name,
                        "price": barcode.price,
                        "measure": barcode.measure,
                        "tmctype": barcode.tmctype,
                        "qdefault": barcode.qdefault,
                    },
                )
                await add_to_autoupdate_ean(
                    barcode.bcode, barcode.dcode, barcode.op_mode, barcode.tmctype
                )
                await update_status_barcode(barcode.id, True)
            s.commit()


async def update_price_in_cash(ip, cash):
    engine = create_engine(
        f"mysql+pymysql://{config.cash_user}:{config.cash_password}@{ip}:{config.port}/{config.cash_database}?charset=utf8mb4",
        pool_recycle=3600,
        pool_timeout=30,
    )
    Session = sessionmaker(bind=engine)
    barcodes_for_price = await get_barcodes_for_price(cash)
    if len(barcodes_for_price) > 0:
        with Session() as s:
            for barcode in barcodes_for_price:
                logger.debug(f"Обновил цену  {barcode.bcode}={barcode.price}")
                s.execute(
                    text(
                        f"UPDATE barcodes JOIN tmc ON barcodes.code = tmc.code SET barcodes.price = {barcode.price}, tmc.price = {barcode.price} WHERE barcodes.barcode = '{barcode.bcode}';"
                    )
                )
                await update_status_barcode(barcode.id, True)
            s.commit()


async def update_all_in_sql():
    for cash_number in get_unique_cashnumbers_from_barcodes():
        cash_info = get_cash_info(cash_number.split("-")[1])
        if cash_info:
            try:
                await add_barcodes_in_cash(
                    cash_info.ip, await get_barcodes_for_add(cash_number)
                )
                await update_price_in_cash(cash_info.ip, cash_number)
            except sqlalchemy.exc.OperationalError as ex:
                if re.findall(r"Can't connect to MySQL server", str(ex)):
                    print(f"Не в сети {cash_info.ip}")


def get_category_by_heuristics(name: str, alcoholpercent: float | None) -> int | None:
    name = name.lower()

    alcohol_keywords = [
        "вино", "вина", "винный",
        "шампанское", "игристое", "просекко", "кава", "креман",
        "водка", "коньяк", "бренди", "виски", "ром", "текила", "ликер", "самогон", "арманьяк",
        "наливка", "настойка", "абсент",
        "мартини", "вермут", "кампари", "чача", "граппа",
        "алк.напиток", "алкоголь", "спирт", "спиртной", "спиртное",
        "аперитив", "дистиллят", "бугульма",
        "ликероводочный", "лвз", "напиток крепкий",
        "крепкий напиток", "горілка", "солод"
    ]
    beer_keywords = [
        "пиво", "пивной", "пивное",
        "lager", "лагер", "пильзнер", "пилснер", "бокбир", "портер", "стаут", "эль", "ipa", "ipa-эль", "индийский эль",
        "нефильтрованное", "фильтрованное", "разливное", "крафтовое", "крепкое пиво",
        "пшеничное", "темное", "светлое", "пивоварня", "пивзавод", "пивко", "хмельное",
        "барливайн", "витбир", "гёз", "ламбик", "брют IPA", "trappist", "belgian ale",
        "бир", "бирмейстер", "бирхаус", "пивбар", "пивовар", "медовуха"
    ]
    tobacco_keywords = [
        "сигареты", "сигарета", "сигариллы", "сигарилла", "сигара", "сигары", "табак", "никотин",
        "табачный", "курительный", "курение", "курить", "дым", "iqos", "glo", "heets", "neo", "sticks", "стики",
        "нагреваемые стики", "табачные стики",
        "вейп", "вейпы", "электронные сигареты", "электронная сигарета", "сиги",
        "pods", "pod", "juul", "vaporesso", "vape", "электронка", "pod-система", "жидкость для вейпа",
        "ник.содержащий", "никотиносодержащий", "бестабачный никотин", "30мл", "дуал",
        "нюхательный табак", "жевательный табак", "снюс", "таблетка никотиновая"
    ]
    markirovka_keywords = [
        "молоко", "молочный", "кефир", "ряженка", "простокваша", "йогурт", "айран", "тан", "снежок",
        "сливки", "творог", "сырок", "биойогурт", "ацидофилин", "бифидок", "заправка молочная",
        "масса творожная", "творожок", "мол. напиток", "молочная продукция", "сыр",
        "вода", "минеральная", "газированная", "негазированная", "питьевая", "вода столовая",
        "байкал", "шишкин лес", "боржоми", "есентуки", "новотерская", "святой источник",
        "aqua", "aqua minerale", "bon aqua", "bonaqua",
        "энергетик", "energy", "энерджи", "burn", "адреналин", "red bull", "gorilla", "drive",
        "монстр", "monster", "black energy", "flash energy", "dark dog", "hussar energy",
        "энергонапиток", "power up", "hell energy", "pulse",
        "лимонад", "напиток", "газированный", "кола", "фанта", "спрайт", "тархун", "дюшес", "ситро",
        "буратино", "черноголовка", "pepsi", "coca-cola", "sprite", "fanta", "mirinda",
        "газ. напиток", "сладкий напиток", "чайный напиток", "ice tea", "чай со льдом", "чай липтон",
        "безалкогольное пиво", "безалк пиво", "0%", "alc 0", "без алкоголя", "пиво 0%", "alcohol-free",
        "non-alcoholic", "пиво безалкогольное", "pils 0%", "lager 0%", "heineken 0", "bud 0", "bavaria 0"
    ]

    if any(kw in name for kw in alcohol_keywords):
        if alcoholpercent and alcoholpercent > 10:
            return 1, 0.99
        return 1, 0.85

    if any(kw in name for kw in beer_keywords):
        if alcoholpercent and 0.5 < alcoholpercent < 10:
            return 2, 0.9
        return 2, 0.75

    if any(kw in name for kw in tobacco_keywords):
        return 3, 0.95

    if any(kw in name for kw in markirovka_keywords):
        return 5, 0.9

    return None


def classify_with_model_and_heuristics(
    name: str, alcoholpercent: float | None, model,
    confidence_threshold: float = 0.75, heuristic_threshold: float = 0.8
) -> int:
    name_lower = name.lower()

    model_proba = model.predict_proba([name_lower])[0]
    model_label = model.classes_[model_proba.argmax()]
    model_confidence = max(model_proba)

    heuristic_result = get_category_by_heuristics(name_lower, alcoholpercent)

    if heuristic_result:
        heuristic_label, heuristic_confidence = heuristic_result

        if model_confidence < confidence_threshold and heuristic_confidence >= heuristic_threshold:
            return heuristic_label

    return model_label


def classify_tmc_item(item):
    return item, classify_with_model_and_heuristics(item.name, item.alcoholpercent, model)


async def process_batch(batch, loop, pool, Session):
    async with Session() as db:
        results = await asyncio.gather(*[
            loop.run_in_executor(pool, classify_tmc_item, item)
            for item in batch
        ])

        for item, dcode in results:
            bcode = item.bcode
            await db.execute(
                update(TMC)
                .where(TMC.bcode == bcode)
                .values(dcode=dcode)
            )
            print(f'{item.name} -> {dcode}')
            if item.minprice < 35 and dcode == 1:
                await db.execute(
                    update(TMC)
                    .where(TMC.bcode == bcode)
                    .values(price_mode=2)
                )

        await db.commit()
        return results

async def update_dcode_in_tmc(ip: str):
    engine = create_async_engine(
        f"mysql+aiomysql://{config.cash_user}:{config.cash_password}@{ip}:{config.port}/{config.cash_database}?charset=utf8mb4",
        pool_recycle=3600,
        pool_timeout=30,
    )
    Session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with Session() as session:

        await session.execute(
            update(TMC)
            .where(TMC.price_mode == 2)
            .values(price_mode=1)
        )
        await session.commit()

        tmc_items = (await session.execute(select(TMC))).scalars().all()

    loop = asyncio.get_running_loop()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        batch_tasks = []

        for i in range(0, len(tmc_items), BATCH_SIZE):
            batch = tmc_items[i:i + BATCH_SIZE]
            task = asyncio.create_task(process_batch(batch, loop, pool, Session))
            batch_tasks.append(task)

            if len(batch_tasks) >= PARALLEL_BATCHES:
                await asyncio.gather(*batch_tasks)
                batch_tasks = []

        if batch_tasks:
            await asyncio.gather(*batch_tasks)


if __name__ == "__main__":
    asyncio.run(update_all_in_sql())
