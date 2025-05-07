from datetime import timedelta
from pathlib import Path

import pandas as pd

import config
from core.database.query_BOT import Database
from core.utils.foreman.foreman import get_actual_all_cashes
from core.utils.foreman.pd_model import ForemanCash


class Report:
    def __init__(self, output_dir: Path, cashes: list[ForemanCash] = None):
        self.output_dir = output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        self.df = None
        self.cashes = [] if not cashes else cashes

    async def get_cashes(self):
        self.cashes = await get_actual_all_cashes(timedelta(days=180))

    async def get_expired_date_rutokens(self) -> None:
        db = Database()
        data = [
            {
                "Магазин": c.shopcode,
                "Касса": c.cashcode,
                "Рутокен ООО": c.gost1_date_end,
                "Рутокен ИП": c.gost2_date_end,
                "Название Магазина": c.artix_shopname,
                "Сотовые": ", ".join(
                    set(
                        [
                            c.phone_number
                            for c in await db.get_clients_by_shopcodes([c.shopcode])
                        ]
                    )
                ),
                "Адрес": c.address,
            }
            for c in self.cashes
        ]
        self.df = pd.DataFrame(data)
        self.df.sort_values(by="Рутокен ООО", ascending=False)

    async def get_mols(self) -> None:
        db = Database()
        data = [
            {
                "Магазин": c.shopcode,
                "Касса": c.cashcode,
                "Кассиры": c.artix_mols,
                "Название Магазина": c.artix_shopname,
                "Сотовые": ", ".join(
                    set(
                        [
                            c.phone_number
                            for c in await db.get_clients_by_shopcodes([c.shopcode])
                        ]
                    )
                ),
                "Адрес": c.address,
            }
            for c in self.cashes
        ]
        self.df = pd.DataFrame(data)

    async def write_to_excel(
        self, file_name: str, autuofilter: bool = True, autowidth: bool = True
    ) -> Path:
        # Проверяем наличия окончания .xlsx иначе дописываем его
        if file_name.endswith(".xlsx"):
            file_path = self.output_dir / file_name
        else:
            file_path = self.output_dir / f"{file_name}.xlsx"

        # Записываем данные в Excel с использованием XlsxWriter
        with pd.ExcelWriter(str(file_path), engine="xlsxwriter") as writer:
            sheet_name = "info"
            self.df.to_excel(writer, sheet_name=sheet_name, index=False, na_rep="NaN")

            # Определяем рабочий лист
            worksheet = writer.sheets[sheet_name]

            # Устанавливаем автофильтр на диапазон данных
            if autuofilter:
                max_row, max_col = self.df.shape
                worksheet.autofilter(0, 0, max_row, max_col - 1)
            # Устанавливаем ширину колонок на основе максимальной длины данных
            if autowidth:
                for i, column in enumerate(self.df.columns):
                    column_length = max(
                        self.df[column].astype(str).map(len).max(), len(column)
                    )
                    worksheet.set_column(i, i, column_length + 3)

        return file_path


async def test():
    dir = Path(config.dir_path) / "files" / "reports"
    report = Report(dir)
    await report.get_cashes()
    await report.get_expired_date_rutokens()
    print(await report.write_to_excel("expired_rutokens"))
    await report.get_mols()
    print(await report.write_to_excel("mols", autowidth=False))


if __name__ == "__main__":
    import asyncio

    asyncio.run(test())
