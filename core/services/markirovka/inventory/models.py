import asyncio
from typing import Union

import pandas as pd
from pydantic import BaseModel, Field, field_validator


class CIS(BaseModel):
    name: str
    gtin: str
    cis: str = Field(default="")
    pg_name: str

    @field_validator("cis")
    def replace_cis(cls, v: str):
        return v.replace("(21)", "").replace("(01)", "")

    @field_validator("gtin")
    def replace_gtin(cls, v: str):
        return f'{"0" * (14 - len(v))}{v}' if len(v) < 14 else v


class ProductVolume(BaseModel):
    name: str = Field(
        default="", title="Нужно для удобного доступа к имени, в честный знак не уходит"
    )
    gtin: str
    gtin_quantity: int
    cises: list[CIS] = Field(
        default=[],
        title="Нужно для удобного доступа к маркам, в честный знак не уходит",
    )

    @field_validator("gtin")
    def replace_gtin(cls, v: str):
        return f'{"0" * (14 - len(v))}{v}' if len(v) < 14 else v


class ProductMarks(BaseModel):
    """4.2.8. Вывод из оборота"""

    cis: str
    product_cost: int = Field(default=None, title="Цена за единицу")
    primary_document_type: str = Field(default=None, title="Тип первичного документа")
    primary_document_number: str = Field(
        default=None, title="Номер первичного документа"
    )
    primary_document_date: str = Field(default=None, title="Дата первичного документа")
    primary_document_custom_name: str = Field(
        default=None, title="Наименование первичного документа"
    )

    @field_validator("cis")
    def replace_cis(cls, v: str):
        return v.replace("(21)", "").replace("(01)", "")


class InventoryExcel(BaseModel):
    pg_name: str
    count_positions: int = Field(default=0)
    count: int = Field(default=0)
    excel_path: str


class Inventory(BaseModel):
    inn: str
    pg_name: str = Field(default="", title="Товарная группа")
    action: str
    primary_document_custom_name: str = Field(
        default="Инвентаризация", title="Название первичного документа"
    )
    action_date: str
    document_type: str
    document_number: str
    document_date: str
    products_inventory: list[Union[ProductVolume, ProductMarks]] = Field(
        default=[], title="Продукты которые отсканировали во время инвентаризации"
    )
    products_balance: list[ProductVolume] = Field(
        default=[], title="Продукты на балансе магазина"
    )
    products_withdraw: list[Union[ProductVolume, ProductMarks]] = Field(
        default=[], alias="products", title="Продукты которые спишутся"
    )

    def get_withdrawal_inventory(
        self, volume_balance: bool = False, by_alias: bool = False
    ):
        inventory = self.model_copy()
        if volume_balance:
            for product_b in inventory.products_balance:
                find = False
                for product_i in inventory.products_inventory:
                    if product_i.gtin == product_b.gtin:
                        find = True
                        inventory.products_withdraw.append(
                            ProductVolume(
                                gtin=product_i.gtin,
                                gtin_quantity=product_b.gtin_quantity
                                - product_i.gtin_quantity,
                            )
                        )
                        break
                if not find:
                    inventory.products_withdraw.append(
                        ProductVolume(
                            gtin=product_b.gtin, gtin_quantity=product_b.gtin_quantity
                        )
                    )
            result_inventory = inventory.model_dump_json(
                by_alias=by_alias,
                exclude_none=True,
                exclude={
                    "products_balance": True,
                    "products_inventory": True,
                    "pg_name": True,
                    "products_withdraw": {"__all__": {"name", "cises"}},
                },
            )
        else:
            cises_i = [c.cis for pi in inventory.products_inventory for c in pi.cises]
            for product_b in inventory.products_balance:
                for pb_cis in product_b.cises:
                    if pb_cis.cis not in cises_i:
                        inventory.products_withdraw.append(ProductMarks(cis=pb_cis.cis))
            result_inventory = inventory.model_dump_json(
                by_alias=by_alias,
                exclude_none=True,
                exclude={
                    "products_balance": True,
                    "products_inventory": True,
                    "pg_name": True,
                },
            )
        return result_inventory

    async def create_excel_withdraw(self, save_path: str) -> InventoryExcel:
        inventory = self.model_copy()
        inventory.model_rebuild()
        for product_b in inventory.products_balance:
            find = False
            for product_i in inventory.products_inventory:
                if product_i.gtin == product_b.gtin:
                    find = True
                    inventory.products_withdraw.append(
                        ProductVolume(
                            name=product_b.name,
                            gtin=product_b.gtin,
                            gtin_quantity=product_b.gtin_quantity
                            - product_i.gtin_quantity,
                        )
                    )
            if not find:
                inventory.products_withdraw.append(
                    ProductVolume(
                        name=product_b.name,
                        gtin=product_b.gtin,
                        gtin_quantity=product_b.gtin_quantity,
                    )
                )
        model = inventory.model_dump(
            include={"products_withdraw"},
            exclude={"products_withdraw": {"__all__": {"cises"}}},
        )["products_withdraw"]
        df = pd.DataFrame(model)
        df.columns = ["Название", "Штрихкод", "Количество"]
        df = df[df["Количество"] > 0]
        df = df.sort_values(by=["Количество"], ascending=False)
        with pd.ExcelWriter(save_path, engine="xlsxwriter") as wb:
            df.to_excel(wb, sheet_name="Инвентаризация", index=False)
            sheet = wb.sheets["Инвентаризация"]
            sheet.autofilter("A1:C" + str(df.shape[1]))
            sheet.set_column("A:A", 50)
            sheet.set_column("B:B", 15)
            sheet.set_column("C:C", 15)
        return InventoryExcel(
            pg_name=inventory.pg_name,
            excel_path=save_path,
            count_positions=len(df.index),
            count=int(df["Количество"].sum()),
        )

    async def create_excel_actual_progress(self, save_path: str) -> InventoryExcel:
        inventory = self.model_copy()
        model = inventory.model_dump(
            include={"products_inventory"},
            exclude={"products_inventory": {"__all__": {"cises"}}},
        )["products_inventory"]
        df = pd.DataFrame(model)
        df.columns = ["Название", "Штрихкод", "Количество"]
        df = df.sort_values(by=["Количество"], ascending=False)
        with pd.ExcelWriter(save_path, engine="xlsxwriter") as wb:
            df.to_excel(wb, sheet_name="Инвентаризация", index=False)
            sheet = wb.sheets["Инвентаризация"]
            sheet.autofilter("A1:C" + str(df.shape[1]))
            sheet.set_column("A:A", 50)
            sheet.set_column("B:B", 15)
            sheet.set_column("C:C", 15)
        return InventoryExcel(
            pg_name=inventory.pg_name,
            excel_path=save_path,
            count_positions=len(df.index),
            count=int(df["Количество"].sum()),
        )
