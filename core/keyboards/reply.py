from aiogram.types import WebAppInfo
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def getKeyboard_registration():
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="Регистрация", request_contact=True)
    keyboard.adjust(1)
    return keyboard.as_markup(one_time_keyboard=True)


def scanner():
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(
        text="📸Сканер📸",
        web_app=WebAppInfo(url="https://minimalon.github.io/ttn"),
        resize_keyboard=True,
        is_persistent=True,
    )
    return keyboard.as_markup()


def one_time_scanner():
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(
        text="📸Сканер📸",
        web_app=WebAppInfo(url="https://minimalon.github.io/one_time_scane/"),
        resize_keyboard=True,
        is_persistent=True,
    )
    return keyboard.as_markup()
