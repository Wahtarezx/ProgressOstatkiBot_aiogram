from pydantic import BaseModel, Field

from core.services.egais.goods.pd_models import Dcode, OpMode, TmcType
from core.services.markirovka.enums import GroupIds


class TovarGroup(BaseModel):
    dcode: Dcode = Field(..., title="Отдел товара")
    op_mode: OpMode = Field(..., title="битовая маска свойств товара")
    tmctype: TmcType = Field(..., title="Тип товара")
    group_id: GroupIds = Field(..., title="ID группы")
    is_volume_balance: bool = Field(..., title="Тип хранения в ЧЗ")
    name: str = Field(..., title="Название группы")
