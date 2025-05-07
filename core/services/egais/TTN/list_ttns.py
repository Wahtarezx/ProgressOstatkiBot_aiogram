import re
import socket

import paramiko
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from bs4 import BeautifulSoup

import config
from core.keyboards.inline import kb_choose_list_ttn, kb_info_ttn, kb_whatsapp_url
from core.loggers.egais_logger import LoggerEGAIS
from core.services.egais.TTN.pd_model import Waybills
from core.utils import texts
from core.utils.callbackdata import ListTTN
from core.utils.foreman.pd_model import ForemanCash


async def choose_list_ttns(call: CallbackQuery, state: FSMContext, log_e: LoggerEGAIS):
    await call.message.edit_text("Загрузка накладных...")
    data = await state.get_data()
    wb = Waybills.model_validate_json(data.get("wb"))
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    ttnload = "ttnload2" if wb.port == "18082" else "ttnload"
    log_e.info(f'Cписок накладных из "{ttnload}"')
    ttns_info = []
    client = paramiko.SSHClient()
    try:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=cash.ip(),
            username=config.user_ssh,
            password=config.password_ssh,
            port=config.port_ssh,
            timeout=5,
        )
        stdin, stdout, stderr = client.exec_command(
            f"find /root/{ttnload}/TTN -name WayBill_v* | sort | tail -n10"
        )
        if stderr.read():
            msg = await texts.error_message_wp(cash, stderr.read().decode("utf-8"))
            await call.message.answer(
                texts.error_head + stderr.read().decode("utf-8"),
                reply_markup=kb_whatsapp_url(msg),
            )
            return
        ttns_path = stdout.read().split()
        for ttn in ttns_path:
            ttn_egais = ttn.decode("utf-8").split("/")[4]
            stdin, stdout, stderr = client.exec_command(f'cat {ttn.decode("utf-8")}')
            tree = BeautifulSoup(stdout.read(), "xml").Documents.Document.WayBill_v4
            shipper_name = tree.Header.Shipper.UL.ShortName.text
            date = tree.Header.Date.text
            wbnumber = tree.Header.NUMBER.text
            ttns_info.append([date, wbnumber, shipper_name, ttn_egais])
    except socket.timeout as e:
        text = "Компьютер не в сети. Возможно он выключен, или нет интернета."
        msg = await texts.error_message_wp(cash, text)
        await call.message.answer(
            texts.error_head + text, reply_markup=kb_whatsapp_url(msg)
        )
        return
    finally:
        client.close()
    log_e.info(f'Вывел накладные "{ttns_info}"')
    await call.message.edit_text(
        "Выберите накладную", reply_markup=kb_choose_list_ttn(ttns_info, ttnload)
    )


async def info_ttn(
    call: CallbackQuery, state: FSMContext, callback_data: ListTTN, log_e: LoggerEGAIS
):
    await call.message.edit_text("Загрузка накладной...")
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data.get("foreman_cash"))
    ttnload, ttn_egais = callback_data.ttnload, callback_data.ttn_e
    log_e.info(f"Выбрали накладную '{ttn_egais}' из папки '{ttnload}'")
    client = paramiko.SSHClient()
    ttn_path = f"/root/{ttnload}/TTN/{ttn_egais}"
    status = None
    text = "ℹ️Статус накладной️:"
    try:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=cash.ip(),
            username=config.user_ssh,
            password=config.password_ssh,
            port=config.port_ssh,
            timeout=5,
        )
        stdin, stdout_wb, stderr = client.exec_command(f"cat {ttn_path}/WayBill_v*")
        if stderr.read():
            msg = await texts.error_message_wp(cash, stderr.read().decode("utf-8"))
            await call.message.answer(
                texts.error_head + stderr.read().decode("utf-8"),
                reply_markup=kb_whatsapp_url(msg),
            )
            return
        stdin, ls, stderr = client.exec_command(f"ls {ttn_path}")
        stdin, grep, stderr = client.exec_command(
            f"grep OperationComment {ttn_path}/Ticket.xml | cut -d '<' -f2 | cut -d '>' -f2"
        )
        grep = grep.read().decode("utf-8")
        tree = BeautifulSoup(stdout_wb.read(), "xml").Documents.Document.WayBill_v4
        if grep:
            if re.findall("подтверждена", grep):
                text += "<b><u>Подтверждена</u></b>✅\n"
                status = "подтверждена"
            elif re.findall("отменен", grep):
                text += "<b><u>Ожидает действий от получателя</u></b>\n"
                status = "ожидает"
            elif re.findall("отозвана", grep):
                text += "<b><u>Поставщик отозвал накладную</u></b>\n"
                status = "ожидает"
            elif re.findall("отказана", grep):
                text += "<b><u>Отказана</u></b>❌\n"
                status = "отказана"
            else:
                text += f"<b><u>{grep}</u></b>\n"
        else:
            status = "ожидает"
            text += "<b><u>Ожидает действий от получателя</u></b>\n"
        shipper_inn = tree.Header.Shipper.UL.INN.text
        text += f"Поставщик: <code>{tree.Header.Shipper.UL.ShortName.text}</code>\n"
        text += f"Номер накладной: <code>{tree.Header.NUMBER.text}</code>\n"
        text += f"Дата накладной: <code>{tree.Header.Date.text}</code>\n"
        text += f"Номер накладной в ЕГАИС: <code>{ttn_egais}</code>\n"
        text += "➖" * 15 + "\n"
        text += "Название | Количество\n"
        text += "➖" * 15 + "\n"
        for product in tree.findAll("Position"):
            Fullname = product.find("FullName").text
            shortname = product.find("{http://fsrar.ru/WEGAIS/ProductRef_v2}ShortName")
            shortName = shortname.text if shortname is not None else False
            capacity = (
                f"{product.find('Capacity').text[:4]}"
                if product.find("Capacity")
                else ""
            )
            quantity = (
                product.find("Quantity").text if product.find("Quantity") else "?"
            )
            if shortName:
                text += f"{shortName} {capacity}л | {quantity} шт\n"
            else:
                text += f"{Fullname} {capacity}л | {quantity} шт\n"
    except socket.timeout as e:
        text = "Компьютер не в сети. Возможно он выключен, или нет интернета."
        msg = await texts.error_message_wp(cash, text)
        await call.message.answer(
            texts.error_head + text, reply_markup=kb_whatsapp_url(msg)
        )
        return
    finally:
        client.close()
    await call.answer()

    await call.message.answer(
        text, reply_markup=kb_info_ttn(status, ttn_egais, shipper_inn)
    )
