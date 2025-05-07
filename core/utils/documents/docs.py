from pathlib import Path

from core.utils.documents.pd_model import WB4, Position, Box
import xmltodict
from bs4 import BeautifulSoup


class Documents:
    def __init__(self, doc_paths: list[Path]):
        self.doc_paths = doc_paths

    async def wb_model(self) -> list[WB4]:
        result = []
        for doc in self.doc_paths:
            with open(doc, "r", encoding="utf-8") as f:
                bs = BeautifulSoup(f.read(), "xml")
                positions = [
                    Position(
                        id=pos.find("wb:Identity").text,
                        product=xmltodict.parse(pos.find("wb:Product").decode())[
                            "wb:Product"
                        ],
                        quantity=pos.find("wb:Quantity").text,
                        price=pos.find("wb:Price").text,
                        ean=pos.find("wb:EAN13").text,
                        boxs=[
                            Box(
                                number=(
                                    box.find("ce:boxnumber").text
                                    if box.find("ce:boxnumber") is not None
                                    else None
                                ),
                                amcs=[
                                    amc.text.strip() for amc in box.find_all("ce:amc")
                                ],
                            )
                            for box in pos.findAll("ce:boxpos")
                        ],
                    )
                    for pos in bs.findAll("wb:Position")
                ]
                wb = WB4(
                    fsrar=bs.find("ns:FSRAR_ID").text,
                    ttn_info=xmltodict.parse(bs.find("wb:Header").decode())[
                        "wb:Header"
                    ],
                    shipper=xmltodict.parse(
                        bs.find("wb:Shipper").find("oref:UL").decode()
                    )["oref:UL"],
                    consignee=xmltodict.parse(
                        bs.find("wb:Consignee").find("oref:UL").decode()
                    )["oref:UL"],
                    contents=positions,
                    file_path=doc,
                )
                result.append(wb)
        return result
