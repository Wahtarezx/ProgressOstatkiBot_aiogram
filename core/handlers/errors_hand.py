from aiogram.fsm.context import FSMContext
from aiogram.types import ErrorEvent
from aiogram.utils.formatting import as_line

from core.keyboards import inline
from core.loggers.egais_logger import LoggerEGAIS
from core.loggers.make_loggers import except_log
from core.utils import texts
from core.utils.foreman.pd_model import ForemanCash


async def error_tgBadRequest(event: ErrorEvent, log_e: LoggerEGAIS):
    if event.update.message is not None:
        log_e.error(str(event.exception))
        await event.update.message.answer(
            **as_line(texts.error_head + str(event.exception)).as_kwargs()
        )
    else:
        await event.update.callback_query.answer("Не нажимайте 2 раза подряд на кнопку")
    except_log.exception(event.exception)
    return


async def error_valueError(event: ErrorEvent, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    log_e.error(str(event.exception))
    except_log.exception(event.exception)
    msg = await texts.error_message_wp(cash, str(event.exception))
    if event.update.message is not None:
        await event.update.message.answer(
            **as_line(texts.error_head + str(event.exception)).as_kwargs(),
            reply_markup=inline.kb_whatsapp_url(msg)
        )
    else:
        await event.update.callback_query.message.answer(
            **as_line(texts.error_head + str(event.exception)).as_kwargs(),
            reply_markup=inline.kb_whatsapp_url(msg)
        )


async def error_validationError(
    event: ErrorEvent, state: FSMContext, log_e: LoggerEGAIS
):
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    errors_to_wp = "\n".join([error["msg"] for error in event.exception.errors()])
    errors = event.exception.errors()
    log_e.error(str(event.exception))
    if "Value error" not in str(event.exception):
        log_e.exception(event.exception)
    for error in errors:
        log_e.error(str(error))
        msg = await texts.error_message_wp(cash, errors_to_wp)
        if event.update.message is not None:
            await event.update.message.answer(
                **as_line(texts.error_head + error["msg"]).as_kwargs(),
                reply_markup=inline.kb_whatsapp_url(msg)
            )
        else:
            await event.update.callback_query.message.answer(
                **as_line(texts.error_head + error["msg"]).as_kwargs(),
                reply_markup=inline.kb_whatsapp_url(msg)
            )


async def error_ConnectionError(
    event: ErrorEvent, state: FSMContext, log_e: LoggerEGAIS
):
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    log_e.error(str(event.exception))
    except_log.exception(event.exception)
    msg = await texts.error_message_wp(cash, str(event.exception))
    if event.update.message is not None:
        await event.update.message.answer(
            **as_line(texts.error_head + str(event.exception)).as_kwargs(),
            reply_markup=inline.kb_whatsapp_url(msg)
        )
    else:
        await event.update.callback_query.message.answer(
            **as_line(texts.error_head + str(event.exception)).as_kwargs(),
            reply_markup=inline.kb_whatsapp_url(msg)
        )


async def error_total(event: ErrorEvent, state: FSMContext, log_e: LoggerEGAIS):
    log_e.exception(event.exception)
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    log_e.error(str(event.exception))
    except_log.exception(event.exception)
    msg = await texts.error_message_wp(cash, str(event.exception))
    if event.update.message is not None:
        await event.update.message.answer(
            **as_line(texts.error_head + str(event.exception)).as_kwargs(),
            reply_markup=inline.kb_whatsapp_url(msg)
        )
        # if str(event.exception):
        #     await event.update.message.bot.send_message(
        #         5263751490,
        #         **as_line(texts.error_head + str(event.exception)).as_kwargs(),
        #         reply_markup=inline.kb_whatsapp_url(msg)
        #     )
    else:
        await event.update.callback_query.message.answer(
            **as_line(texts.error_head + str(event.exception)).as_kwargs(),
            reply_markup=inline.kb_whatsapp_url(msg)
        )
        # if str(event.exception):
        #     await event.update.callback_query.message.bot.send_message(
        #         5263751490,
        #         **as_line(texts.error_head + str(event.exception)).as_kwargs(),
        #         reply_markup=inline.kb_whatsapp_url(msg)
        #     )


async def error_sqlalchemy(event: ErrorEvent, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    error_code = event.exception.orig.args[0]
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    log_e.error(str(event.exception))
    except_log.exception(event.exception)
    if error_code == 1712:
        error_msg = "Индекс повреждён, необходимо восстановление индекса."
    elif error_code == 2003:
        error_msg = texts.error_cashNotOnline
    elif error_code == 1045:
        error_msg = "Нажмите кнопку /clear в меню бота, и попробуйте заново."
    elif error_code == 2013:
        error_msg = "Произошел разрыв подключения. Попробуйте повторить снова тоже действие."
    else:
        error_msg = str(event.exception)
    msg = await texts.error_message_wp(cash, error_msg)
    if event.update.message is not None:
        await event.update.message.answer(
            **as_line(texts.error_head + error_msg).as_kwargs(),
            reply_markup=inline.kb_whatsapp_url(msg)
        )
    else:
        await event.update.callback_query.message.answer(
            **as_line(texts.error_head + error_msg).as_kwargs(),
            reply_markup=inline.kb_whatsapp_url(msg)
        )


async def error_EDO(event: ErrorEvent, state: FSMContext, log_e: LoggerEGAIS):
    data = await state.get_data()
    cash = ForemanCash.model_validate_json(data["foreman_cash"])
    log_e.error(str(event.exception))
    except_log.exception(event.exception)
    msg = await texts.error_message_wp(cash, str(event.exception))
    if event.update.message is not None:
        await event.update.message.answer(
            **as_line(texts.error_head + str(event.exception)).as_kwargs(),
            reply_markup=inline.kb_whatsapp_url(msg)
        )
        # if "В параметре inn должен быть передан ИНН организации" not in str(
        #     event.exception
        # ) and "Отсутствуют доверенности" not in str(event.exception):
            # if str(event.exception):
            #     await event.update.message.bot.send_message(
            #         5263751490,

            #         **as_line(texts.error_head + str(event.exception)).as_kwargs(),
            #         reply_markup=inline.kb_whatsapp_url(msg)
            #     )
    else:
        await event.update.callback_query.message.answer(
            **as_line(texts.error_head + str(event.exception)).as_kwargs(),
            reply_markup=inline.kb_whatsapp_url(msg)
        )
        # if "В параметре inn должен быть передан ИНН организации" not in str(
        #     event.exception
        # ) and "Отсутствуют доверенности" not in str(event.exception):
            # if str(event.exception):
            #     await event.update.callback_query.message.bot.send_message(
            #         5263751490,
            #         **as_line(texts.error_head + str(event.exception)).as_kwargs(),
            #         reply_markup=inline.kb_whatsapp_url(msg)
            #     )
