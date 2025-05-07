#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os.path
from datetime import datetime
from bs4 import BeautifulSoup
import config
from lxml import etree


def WayBillAct_v4(ttn, fsrar):
    doc = (
        """<?xml version="1.0" encoding="utf-8"?>
<ns:Documents xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:rap="http://fsrar.ru/WEGAIS/ReplyAP" xmlns:wa="http://fsrar.ru/WEGAIS/ActTTNSingle" xmlns:orefv="http://fsrar.ru/WEGAIS/ReplyClientVersion" xmlns:ains2="http://fsrar.ru/WEGAIS/ActChargeOnShop_v2" xmlns:awr3="http://fsrar.ru/WEGAIS/ActWriteOff_v3" xmlns:wbr2="http://fsrar.ru/WEGAIS/TTNInformF2Reg" xmlns:ctc="http://fsrar.ru/WEGAIS/ConfirmTicket" xmlns:asiut="http://fsrar.ru/WEGAIS/AsiiuTime" xmlns:rfhb="http://fsrar.ru/WEGAIS/ReplyHistFormB" xmlns:rfhb2="http://fsrar.ru/WEGAIS/ReplyHistForm2" xmlns:aint2="http://fsrar.ru/WEGAIS/ActInventoryInformF2Reg" xmlns:rs="http://fsrar.ru/WEGAIS/ReplySpirit" xmlns:pref="http://fsrar.ru/WEGAIS/ProductRef" xmlns:rs2="http://fsrar.ru/WEGAIS/ReplySpirit_v2" xmlns:rap2="http://fsrar.ru/WEGAIS/ReplyAP_v2" xmlns:rsbc="http://fsrar.ru/WEGAIS/ReplyRestBCode" xmlns:rssp="http://fsrar.ru/WEGAIS/ReplySSP" xmlns:awr="http://fsrar.ru/WEGAIS/ActWriteOff" xmlns:oref="http://fsrar.ru/WEGAIS/ClientRef" xmlns:wb2="http://fsrar.ru/WEGAIS/TTNSingle_v2" xmlns:wa3="http://fsrar.ru/WEGAIS/ActTTNSingle_v3" xmlns:rc="http://fsrar.ru/WEGAIS/ReplyClient" xmlns:qf="http://fsrar.ru/WEGAIS/QueryFormAB" xmlns:tc="http://fsrar.ru/WEGAIS/Ticket" xmlns:oref2="http://fsrar.ru/WEGAIS/ClientRef_v2" xmlns:qbc="http://fsrar.ru/WEGAIS/QueryBarcode" xmlns:rbc="http://fsrar.ru/WEGAIS/ReplyBarcode" xmlns:rfb="http://fsrar.ru/WEGAIS/ReplyFormB" xmlns:rfa2="http://fsrar.ru/WEGAIS/ReplyForm1" xmlns:ainp2="http://fsrar.ru/WEGAIS/ActChargeOn_v2" xmlns:wb4="http://fsrar.ru/WEGAIS/TTNSingle_v4" xmlns:rssp2="http://fsrar.ru/WEGAIS/ReplySSP_v2" xmlns:rstm="http://fsrar.ru/WEGAIS/ReplyRests_Mini" xmlns:wbfu="http://fsrar.ru/WEGAIS/InfoVersionTTN" xmlns:rstsm="http://fsrar.ru/WEGAIS/ReplyRestsShop_Mini" xmlns:rsts2="http://fsrar.ru/WEGAIS/ReplyRestsShop_v2" xmlns:rrawo="http://fsrar.ru/WEGAIS/RequestRepealAWO" xmlns:qp="http://fsrar.ru/WEGAIS/QueryParameters" xmlns:ainp="http://fsrar.ru/WEGAIS/ActChargeOn" xmlns:wbr="http://fsrar.ru/WEGAIS/TTNInformBReg" xmlns:rpp="http://fsrar.ru/WEGAIS/RepProducedProduct" xmlns:pref2="http://fsrar.ru/WEGAIS/ProductRef_v2" xmlns:wa2="http://fsrar.ru/WEGAIS/ActTTNSingle_v2" xmlns:rst="http://fsrar.ru/WEGAIS/ReplyRests" xmlns:tts="http://fsrar.ru/WEGAIS/TransferToShop" xmlns:wb="http://fsrar.ru/WEGAIS/TTNSingle" xmlns:qsbc="http://fsrar.ru/WEGAIS/QueryRestBCode" xmlns:ain="http://fsrar.ru/WEGAIS/ActInventorySingle" xmlns:tfs="http://fsrar.ru/WEGAIS/TransferFromShop" xmlns:awrs2="http://fsrar.ru/WEGAIS/ActWriteOffShop_v2" xmlns:awr2="http://fsrar.ru/WEGAIS/ActWriteOff_v2" xmlns:ce="http://fsrar.ru/WEGAIS/CommonEnum" xmlns:qrri="http://fsrar.ru/WEGAIS/QueryRejectRepImported" xmlns:wa4="http://fsrar.ru/WEGAIS/ActTTNSingle_v4" xmlns:rraco="http://fsrar.ru/WEGAIS/RequestRepealACO" xmlns:nattn="http://fsrar.ru/WEGAIS/ReplyNoAnswerTTN" xmlns:c="http://fsrar.ru/WEGAIS/Common" xmlns:rfb2="http://fsrar.ru/WEGAIS/ReplyForm2" xmlns:rrwb="http://fsrar.ru/WEGAIS/RequestRepealWB" xmlns:rst2="http://fsrar.ru/WEGAIS/ReplyRests_v2" xmlns:qrrp="http://fsrar.ru/WEGAIS/QueryRejectRepProduced" xmlns:rfa="http://fsrar.ru/WEGAIS/ReplyFormA" xmlns:aint="http://fsrar.ru/WEGAIS/ActInventoryInformBReg" xmlns:rpi="http://fsrar.ru/WEGAIS/RepImportedProduct" xmlns:ripf1="http://fsrar.ru/WEGAIS/RepInformF1Reg" xmlns:crwb="http://fsrar.ru/WEGAIS/ConfirmRepealWB" xmlns:rc2="http://fsrar.ru/WEGAIS/ReplyClient_v2" xmlns:qf2="http://fsrar.ru/WEGAIS/QueryFormF1F2" xmlns:asiu="http://fsrar.ru/WEGAIS/Asiiu" xmlns:wb3="http://fsrar.ru/WEGAIS/TTNSingle_v3" xmlns:ns="http://fsrar.ru/WEGAIS/WB_DOC_SINGLE_01">
  <ns:Owner>
    <ns:FSRAR_ID>"""
        + str(fsrar)
        + """</ns:FSRAR_ID>
  </ns:Owner>
  <ns:Document>
    <ns:WayBillAct_v4>
      <wa4:Header>
        <wa4:IsAccept>Accepted</wa4:IsAccept>
        <wa4:ACTNUMBER>TTN-"""
        + str(ttn)
        + """</wa4:ACTNUMBER>
        <wa4:ActDate>"""
        + datetime.strftime(datetime.now(), "%Y-%m-%d")
        + """</wa4:ActDate>
        <wa4:WBRegId>TTN-"""
        + str(ttn)
        + """</wa4:WBRegId>
      </wa4:Header>
      <wa4:Transport>
        <wa4:ChangeOwnership>IsChange</wa4:ChangeOwnership>
      </wa4:Transport>
    </ns:WayBillAct_v4>
  </ns:Document>
</ns:Documents>"""
    )
    return doc


def QueryRestsShop_V2(fsrar):
    doc = """<?xml version="1.0" encoding="UTF-8"?>
<ns:Documents Version="1.0"
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xmlns:ns="http://fsrar.ru/WEGAIS/WB_DOC_SINGLE_01"
xmlns:qp="http://fsrar.ru/WEGAIS/QueryParameters">
<ns:Owner>
<ns:FSRAR_ID>{}</ns:FSRAR_ID>
</ns:Owner>
<ns:Document>
<ns:QueryRestsShop_v2>
</ns:QueryRestsShop_v2>
</ns:Document>
</ns:Documents>
    """.format(
        fsrar
    )
    return doc


def QueryRests_v2(fsrar):
    doc = """<ns:Documents xmlns:ns="http://fsrar.ru/WEGAIS/WB_DOC_SINGLE_01" xmlns:qp="http://fsrar.ru/WEGAIS/QueryParameters"
              xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <ns:Owner>
        <ns:FSRAR_ID>{0}</ns:FSRAR_ID>
    </ns:Owner>
    <ns:Document>
        <ns:QueryRests_v2/>
    </ns:Document>
    </ns:Documents>
    """.format(
        fsrar
    )
    return doc


def ActWriteOffShop_v2(fsrar, products_list):
    doc = """<?xml version="1.0" encoding="UTF-8"?>
<ns:Documents xmlns:awr="http://fsrar.ru/WEGAIS/ActWriteOffShop_v2"
    xmlns:ns="http://fsrar.ru/WEGAIS/WB_DOC_SINGLE_01"
    xmlns:oref="http://fsrar.ru/WEGAIS/ClientRef_v2"
    xmlns:pref="http://fsrar.ru/WEGAIS/ProductRef_v2"
    xmlns:unqualified_element="http://fsrar.ru/WEGAIS/CommonEnum"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <ns:Owner>
    <ns:FSRAR_ID>{0}</ns:FSRAR_ID>
  </ns:Owner>
  <ns:Document>
    <ns:ActWriteOffShop_v2>
            <awr:Header>
                <awr:ActNumber>{1}</awr:ActNumber>
                <awr:ActDate>{2}</awr:ActDate>
                <awr:TypeWriteOff>Реализация</awr:TypeWriteOff>
            </awr:Header>
            <awr:Content>\n""".format(
        fsrar,
        str(datetime.utcnow().timestamp()).split(".")[0],
        datetime.strftime(datetime.now(), "%Y-%m-%d"),
    )

    for item in products_list:
        doc += item

    doc += """\t\t\t</awr:Content>
        </ns:ActWriteOffShop_v2>
    </ns:Document>
</ns:Documents>"""
    return doc


def ActWriteOff_v3(fsrar, products_list):
    doc = """<?xml version="1.0" encoding="UTF-8"?>
<ns:Documents xmlns:awr="http://fsrar.ru/WEGAIS/ActWriteOff_v3" xmlns:ce="http://fsrar.ru/WEGAIS/CommonV3"
              xmlns:ns="http://fsrar.ru/WEGAIS/WB_DOC_SINGLE_01" xmlns:oref="http://fsrar.ru/WEGAIS/ClientRef_v2"
              xmlns:pref="http://fsrar.ru/WEGAIS/ProductRef_v2" xmlns:unqualified_element="http://fsrar.ru/WEGAIS/CommonEnum"
              xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <ns:Owner>
        <ns:FSRAR_ID>{0}</ns:FSRAR_ID>
    </ns:Owner>
    <ns:Document>
        <ns:ActWriteOff_v3>
            <awr:Header>
                <awr:ActNumber>{1}</awr:ActNumber>
                <awr:ActDate>{2}</awr:ActDate>
                <awr:TypeWriteOff>Иные цели</awr:TypeWriteOff>
            </awr:Header>
            <awr:Content>\n""".format(
        fsrar,
        str(datetime.utcnow().timestamp()).split(".")[0],
        datetime.strftime(datetime.now(), "%Y-%m-%d"),
    )

    for item in products_list:
        doc += item

    doc += """\t\t\t</awr:Content>
        </ns:ActWriteOff_v3>
    </ns:Document>
</ns:Documents>"""
    return doc


def divirgence_ttn(fsrar, boxes, ttn_egais):
    doc = f"""<?xml version="1.0" encoding="utf-8"?>
<ns:Documents xmlns:pref="http://fsrar.ru/WEGAIS/ProductRef" xmlns:c="http://fsrar.ru/WEGAIS/Common" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:ce="http://fsrar.ru/WEGAIS/CommonV3" xmlns:oref="http://fsrar.ru/WEGAIS/ClientRef" xmlns:wa="http://fsrar.ru/WEGAIS/ActTTNSingle_v4" Version="1.0" xmlns:ns="http://fsrar.ru/WEGAIS/WB_DOC_SINGLE_01">
	<ns:Owner>
		<ns:FSRAR_ID>{fsrar}</ns:FSRAR_ID>
	</ns:Owner>
	<ns:Document>
		<ns:WayBillAct_v4>
			<wa:Header>
				<wa:IsAccept>Differences</wa:IsAccept>
				<wa:ACTNUMBER>TTN-{ttn_egais}</wa:ACTNUMBER>
				<wa:ActDate>{datetime.strftime(datetime.now(), "%Y-%m-%d")}</wa:ActDate>
				<wa:WBRegId>TTN-{ttn_egais}</wa:WBRegId>
				<wa:Note/>
			</wa:Header>
			<wa:Content>\n"""
    for box in boxes:
        doc += "\t\t\t\t<wa:Position>\n"
        doc += f"\t\t\t\t\t<wa:Identity>{box.identity}</wa:Identity>\n"
        doc += f"\t\t\t\t\t<wa:InformF2RegId>{box.informF2RegId}</wa:InformF2RegId>\n"
        doc += f"\t\t\t\t\t<wa:RealQuantity>{box.quantity}</wa:RealQuantity>\n"
        if len(box.amc) > 0:
            doc += "\t\t\t\t\t\t<wa:MarkInfo>\n"
            for amc in box.amc:
                doc += f"\t\t\t\t\t\t\t<ce:amc>{amc}</ce:amc>\n"
            doc += "\t\t\t\t\t\t</wa:MarkInfo>\n"
        doc += "\t\t\t\t</wa:Position>\n"
    doc += """\t\t\t</wa:Content>
		</ns:WayBillAct_v4>
	</ns:Document>
</ns:Documents>"""
    return doc


def QueryRestBCode(fsrar, FB):
    doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<ns:Documents Version="1.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:ns="http://fsrar.ru/WEGAIS/WB_DOC_SINGLE_01" xmlns:qp="http://fsrar.ru/WEGAIS/QueryParameters">
<ns:Owner>
    <ns:FSRAR_ID>{fsrar}</ns:FSRAR_ID>
</ns:Owner>
<ns:Document>
    <ns:QueryRestBCode>
    <qp:Parameters>
        <qp:Parameter>
            <qp:Name>ФОРМА2</qp:Name>
            <qp:Value>{FB}</qp:Value>
        </qp:Parameter>
    </qp:Parameters>
    </ns:QueryRestBCode>
</ns:Document>
</ns:Documents>"""
    return doc


def QueryResendDoc(fsrar, ttn):
    doc = """<ns:Documents xmlns:ns="http://fsrar.ru/WEGAIS/WB_DOC_SINGLE_01" xmlns:qp="http://fsrar.ru/WEGAIS/QueryParameters" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<ns:Owner>
    <ns:FSRAR_ID>{0}</ns:FSRAR_ID>
</ns:Owner>
<ns:Document>	
    <ns:QueryResendDoc>
        <qp:Parameters>
            <qp:Parameter>
                <qp:Name>WBREGID</qp:Name>
                <qp:Value>{1}</qp:Value>
            </qp:Parameter>
        </qp:Parameters>
    </ns:QueryResendDoc>
</ns:Document>
</ns:Documents>""".format(
        fsrar, ttn
    )
    return doc
