import json
import re
from collections import namedtuple
from funcy import first, where
from loguru import logger

from core.services.markirovka.inventory.models import CIS
from core.services.markirovka.trueapi import TrueApi


async def find_gtins_from_datamatrix(marks: list):
    access = []
    for mark in marks:
        if mark.startswith("010"):
            gtin = re.findall(r"01([0-9]{14})", mark)
        else:
            gtin = re.findall(r"^[0-9]{14}", mark)
        if gtin is not None:
            access.append(gtin[0])
    return access


async def check_cises(cises: list, znak: TrueApi):
    marks_info = namedtuple("cises_info", "error access")
    cises_info = json.loads(znak.check_cises(cises))["codes"]
    gtins_info = await znak.product_info("Здесь должен быть список GTIN")
    gtins_info = [g._asdict() for g in gtins_info]
    errors = []
    access = []
    for cis in cises_info:
        if cis["valid"]:
            access.append(
                CIS(
                    name=first(where(gtins_info, gtin=cis["gtin"]))["name"],
                    cis=cis["cis"],
                    gtin=first(where(gtins_info, gtin=cis["gtin"]))["gtin"],
                    pg_name=first(where(gtins_info, gtin=cis["gtin"]))["productGroup"],
                )
            )
        else:
            errors.append(cis["cis"])
    return marks_info(errors, access)


if __name__ == "__main__":
    a = namedtuple("a", "a b")
    print(json.dumps((a("1", "2"), a("1", "2"))))
