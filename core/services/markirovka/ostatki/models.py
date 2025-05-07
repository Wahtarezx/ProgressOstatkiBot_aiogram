from pathlib import Path

from pydantic import BaseModel, Field

from core.services.markirovka.inventory.models import ProductVolume


class OstatkiCSV(BaseModel):
    csv_path: Path
    excel_path: Path
    count_positions: int = Field(default=0)
    count: int = Field(default=0)
    products: list[ProductVolume] = Field([], title="Продукты")
    error_code: int = Field(default=0)
    error_value: str = Field(default="")


class OstatkiExcel(OstatkiCSV):
    pg_name: str


if __name__ == "__main__":
    a = OstatkiCSV(
        file_path="1",
        count="1",
        error_code="1",
        error_value="1",
    )
