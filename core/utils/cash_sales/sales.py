import json
import zipfile
from datetime import date, datetime, timedelta
from dateutil import parser
from pathlib import Path
import config
from core.loggers.make_loggers import bot_log
from core.utils.cash_sales.pd_model import CashShifts, Shift, ShiftInfo, Check


class CashSales:
    def __init__(self, dir_sales: Path):
        self.dir_sales = dir_sales

    async def get_sorted_zips_by_date(self, desc: bool = True) -> list[Path]:
        zips = [
            x
            for x in self.dir_sales.iterdir()
            if x.name.endswith(".zip")
            # if self.start_date <= date.fromtimestamp(int(x.name[1:].strip('.zip')) / 1000000) < self.end_date
        ]
        zips.sort(key=lambda x: x.stat().st_mtime)
        if desc:
            zips.reverse()
        return zips

    async def _get_json_from_zip(self, zip_path: Path) -> list[dict]:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for name in zip_ref.namelist():
                if name.endswith(".json"):
                    content = zip_ref.read(name).decode("utf-8")
                    json_sections = content.split("---")
                    result = []
                    for section in json_sections:
                        section = section.strip()

                        if not section:
                            continue  # Пропускаем пустые секции

                        lines = [l.strip() for l in section.splitlines()]
                        json_lines = []

                        for line in lines:
                            if line.startswith("###"):
                                continue  # Пропускаем заголовки
                            json_lines.append(line)

                        json_str = "\n".join(json_lines)

                        if not json_str:
                            continue  # Пропускаем, если после удаления заголовков ничего не осталось

                        result.append(json.loads(json_str))
                    return result

    async def get_sales(self, start_date: date, end_date: date) -> CashShifts:
        """
        Парсим json файлы artix с продажами
        """
        shifts: list[Shift] = []
        for zip_path in await self.get_sorted_zips_by_date():
            checks: list[Check] = []
            content = await self._get_json_from_zip(zip_path)
            for obj in content:
                if obj.get("kkms"):
                    shift = ShiftInfo.model_validate_json(json.dumps(obj))
                    shifts.append(Shift(shift=shift, checks=checks))
                else:
                    checks.append(Check.model_validate_json(json.dumps(obj)))

        return await CashShifts(shifts=shifts).get_shifts_by_date(start_date, end_date)


async def test():
    dir_sales = Path(config.server_path, "backup", "sales", "1900", "1")
    start_date = datetime.date(datetime.now()) - timedelta(days=1)
    end_date = datetime.date(datetime.now())
    Sales = CashSales(dir_sales)
    sales = await Sales.get_sales(start_date, end_date)
    print(sales)


if __name__ == "__main__":
    import asyncio

    asyncio.run(test())
