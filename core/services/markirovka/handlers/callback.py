from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from core.loggers.markirovka_logger import LoggerZnak
from core.services.edo.schemas.login.models import Certificate, EnumEdoProvider
from core.services.markirovka.callbackdata import ChoiseEdoProvider
from core.services.markirovka.keyboard.inline import (
    kb_markirovka_doc_menu,
    kb_ostatki_start_menu,
)
from core.services.markirovka.ofdplatforma import OFD
from core.utils import texts


async def documents_menu(call: CallbackQuery, state: FSMContext, log_m: LoggerZnak):
    log_m.button("Накладные")
    data = await state.get_data()
    cert = Certificate.model_validate_json(data["certificate"])
    if cert.edo_provider != EnumEdoProvider.edolite:
        log_m.error(f'Неверный провайдер ЭДО "{cert.edo_provider}"')
        await call.message.answer(
            texts.intersum_head
            + "Работа с документами допустна, если только у вас ЭДО провайдер 'ЭДО Лайт'"
        )
        return
    await call.message.edit_text(
        texts.markirovka_doc_menu, reply_markup=kb_markirovka_doc_menu()
    )


async def ostatki_menu(call: CallbackQuery, log_m: LoggerZnak):
    log_m.button("Остатки")
    await call.message.edit_text(
        "Выберите нужный способ получения остатков",
        reply_markup=kb_ostatki_start_menu(),
    )


if __name__ == "__main__":
    import re

    milk_pattern = r"\s*01(?P<barcode>[0-9]{14})(21.{13}\s*(17\d{6}|7003\d{10})|21.{6}|21.{8})\s*93.{4}(\s*3103(?P<weight>\d{6}))?"
    water_pattern = r"01(?P<barcode>[0-9]{14})21.{13}\s*93.{4}\s*"
    tobacco_pattern = r"[0-9]{14}.{15}|01[0-9]{14}21.{7}8005[0-9]{6}93.{4}."

    eans = [
        "046100171222739ufL_pwAB.AgrhM",
        '04610017122457EM"7y;3AB.AD8Yd',
        "01046700073602072151:YBk93O2AV",
        '04606203103188%K7H8%<AC"8YmEb',
        "010460165303446421T-ffJac800514000093g5uL24002203537",
        "0104670007360511215aFrRK93OBiF",
        "0104607054765655215VfYGl93rjHr",
        "0104612743890259215myD5zjR4XsKq93EHm7",
        "0104680036754069215BrVhPGTyGnvi93tqB5",
        "0104607074063724215./7QQ93c1n2",
        "0104612743890013215d)<ICsc9Ibne93k+PJ",
        "0104603934000250215)7tpMcC1Hh;i932Oo4",
        "0104810268036163212q3hi49o93j3eg",
    ]
    for e in eans:
        if e.startswith("010"):
            gtin = re.findall(r"01([0-9]{14})", e)[0]
        else:
            gtin = re.findall(r"^[0-9]{14}", e)[0]

        print(gtin)
