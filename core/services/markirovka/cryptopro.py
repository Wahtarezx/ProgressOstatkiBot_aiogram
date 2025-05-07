#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys
from base64 import b64encode
from datetime import datetime
from typing import Union

sys.path.append("/opt/pycades_0.1.44290/")

if os.name == "posix":
    import pycades


class CryproPro:
    def __init__(self, thumbprint: str = None, pin: str = ""):
        self.thumbprint = thumbprint
        self.pin = pin
        if os.name == "posix":
            self.signer = self.get_signer()
        self.cert_info = None

    @staticmethod
    def parse_detail(row):
        if row:
            detail = dict(key_val.split("=") for key_val in row.split(", "))
            detail["row"] = row
            return detail

    def certificate_info(self, cert=None):
        """Данные сертификата."""
        if cert is None and self.thumbprint is not None:
            cert = self.get_certificate(self.thumbprint)
        pkey = cert.PrivateKey
        algo = cert.PublicKey().Algorithm

        cert_info = {
            "privateKey": {
                "providerName": pkey.ProviderName,
                "uniqueContainerName": pkey.UniqueContainerName,
                "containerName": pkey.ContainerName,
            },
            "algorithm": {
                "name": algo.FriendlyName,
                "val": algo.Value,
            },
            "valid": {
                "from": cert.ValidFromDate,
                "to": cert.ValidToDate,
            },
            # 'issuer': self.parse_detail(cert.IssuerName),
            "subject": self.parse_detail(cert.SubjectName),
            "thumbprint": cert.Thumbprint,
            "serialNumber": cert.SerialNumber,
            "hasPrivateKey": cert.HasPrivateKey(),
        }
        return cert_info

    def get_certificate(self, thumbprint: str):
        store = pycades.Store()
        store.Open(
            pycades.CADESCOM_CONTAINER_STORE,
            pycades.CAPICOM_MY_STORE,
            pycades.CAPICOM_STORE_OPEN_MAXIMUM_ALLOWED,
        )
        try:
            certificates = store.Certificates.Find(0, thumbprint)
        except Exception as e:
            if "Cannot find object or property" in str(e):
                raise ValueError("Не нашлось сертификата по вашему отпечатку")
            else:
                raise e
        count = 0
        for cert_num in range(certificates.Count):
            cert = certificates.DocumentItem(cert_num + 1)
            cert_info = self.certificate_info(cert)
            if datetime.now() > datetime.strptime(
                cert_info["valid"]["to"], "%d.%m.%Y %H:%M:%S"
            ):
                continue
            count += 1
        if count == 0:
            raise ValueError("Не найден действующий сертификат")
        return cert

    def get_signer(self):
        signer = pycades.Signer()
        signer.Certificate = self.get_certificate(self.thumbprint)
        signer.CheckCertificate = True
        signer.KeyPin = self.pin
        return signer

    def signing_data(self, data):
        """
        Подпись текста (Для получения токена)
        detached - Истина/Ложь - откреплённая(для подписания документов)/прикреплённая(для получения токена авторизации) подпись
        """
        signed_data = pycades.SignedData()
        signed_data.ContentEncoding = pycades.CADESCOM_BASE64_TO_BINARY
        signed_data.Content = data
        signature = signed_data.SignCades(self.signer, pycades.CADESCOM_CADES_BES)
        return signature

    def signing_data_with_user(self, data):
        """
        Подпись текста (Для получения токена)
        detached - Истина/Ложь - откреплённая(для подписания документов)/прикреплённая(для получения токена авторизации) подпись
        """
        signer = pycades.Signer()
        signer.Certificate = self.get_certificate(self.thumbprint)
        signer.CheckCertificate = True
        signer.KeyPin = self.pin
        signer.Options = pycades.CAPICOM_CERTIFICATE_INCLUDE_CHAIN_EXCEPT_ROOT
        signed_data = pycades.SignedData()
        signed_data.ContentEncoding = pycades.CADESCOM_BASE64_TO_BINARY
        signed_data.Content = data
        signature = signed_data.SignCades(signer, pycades.CADESCOM_CADES_BES)
        return signature

    def signing_pdf(self, data):
        signed_data = pycades.SignedData()
        signed_data.Content = b64encode(data).decode()
        return signed_data.SignCades(self.signer, pycades.CADESCOM_CADES_BES)

    def signing_how_in_javascript(self, data, detached=False):
        signed_data = pycades.SignedData()
        signed_data.ContentEncoding = pycades.CADESCOM_BASE64_TO_BINARY
        signed_data.Content = data
        return signed_data.SignCades(self.signer, pycades.CADESCOM_CADES_BES, detached)

    def signing_xml(self, data, encoding="utf-8"):
        """Подпись XML"""
        signedXML = pycades.SignedXML()
        signedXML.Content = data
        signedXML.SignatureType = (
            pycades.CADESCOM_XML_SIGNATURE_TYPE_ENVELOPED | pycades.CADESCOM_XADES_BES
        )
        signature = signedXML.Sign(self.signer)
        return signature

    def signing_hash(self, data: Union[str, bytes, bytearray], encoding="utf-8") -> str:
        """Подпись хэш"""
        if isinstance(data, str):
            data = bytes(data.encode(encoding))

        hashed_data = pycades.HashedData()
        hashed_data.DataEncoding = pycades.CADESCOM_BASE64_TO_BINARY
        hashed_data.Algorithm = pycades.CADESCOM_HASH_ALGORITHM_CP_GOST_3411_2012_256
        hashed_data.Hash(b64encode(data).decode())
        byte_hash = bytes.fromhex(hashed_data.Value)
        return b64encode(byte_hash).decode()

    def read_certificate(self, cert_path):
        with open(cert_path, "rb") as f:
            cert = pycades.Certificate()
            cert.Import(f.read())
        return self.certificate_info(cert)

    def sign_detach_data(
        self, data: str | bytes, file_path: str, encode: str = "windows-1251"
    ) -> str:
        """
        Отсоединённая подпись
        :param data: Данные которые подписывать
        :param file_path: Путь куда сохраним файл подписываем. Также сохраняет подписыванный файл с окончанием .sig
        :param encode: Кодировка
        :return: Подпись в формате base64
        """
        if isinstance(data, str):
            with open(file_path, "wb") as file:
                if data.startswith("%PDF"):
                    encode = "utf-8"
                file.write(data.encode(encode))
        elif isinstance(data, bytes):
            with open(file_path, "wb") as file:
                file.write(data)

        sign = f"/opt/cprocsp/bin/amd64/csptest -sfsign -sign -add -detached -base64 -in {file_path} -out {file_path}.sig -my '{self.thumbprint}'"
        cat = f'cat {file_path}.sig | tr -d "\n"'
        delete = f"rm {file_path}.sig"
        result_sign = subprocess.run(
            sign, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result_sign.returncode != 0:
            raise ValueError(result_sign.stderr)
        result = subprocess.run(
            cat, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        # subprocess.run(delete, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        return result.stdout


if __name__ == "__main__":
    c = CryproPro(thumbprint="dad66e334051569c8f3c837fd04a630b2c676bc6")
    # 51a600957c1b3aa94fc98b53868fe4bd6f4ae7ec Лазорина
    # c.get_signer()
    # with open('/linuxcash/net/server/server/znak/lazorina.cer', "rb") as f:
    #     cert = pycades.Certificate()
    #     cert.Import(f.read())
    #     print(cert.Thumbprint)
