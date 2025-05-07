from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

from core.database.modelBOT import Clients
from core.database.models_enum import Roles
from core.database.query_BOT import Database
from core.loggers.make_loggers import bot_log, except_log

def_commands = [
    BotCommand(command="start", description="🏠Главное меню"),
    BotCommand(command="comp", description="Сменить компьютер🔄🖥"),
    BotCommand(command="clear", description="🧹Очистить кеш"),
    BotCommand(command="id", description="Мой id чата🆔"),
]


async def get_commands_by_role(client: Clients) -> list[BotCommand]:
    result = []
    result.extend(def_commands)
    if client.role.role == Roles.ADMIN.value:
        bot_log.info(
            f"Установлены команды для {Roles(client.role.role).value} {client.chat_id}"
        )
        result.append(BotCommand(command="admin", description="⚙️Админ панель"))
        result.append(
            BotCommand(command="ref", description="🔗Создать реферальную ссылку")
        )
        result.append(BotCommand(command="panel", description="📦Панель поставщика"))
    elif client.role.role == Roles.TEHPOD.value:
        bot_log.info(
            f"Установлены команды для {Roles(client.role.role).value} {client.chat_id}"
        )
        result.append(
            BotCommand(command="ref", description="🔗Создать реферальную ссылку")
        )
    elif client.role.role in [
        Roles.SAMAN_PROVIDER.value,
        Roles.PREMIER_PROVIDER.value,
        Roles.ROSSICH_PROVIDER.value,
    ]:
        bot_log.info(
            f"Установлены команды для {Roles(client.role.role).value} {client.chat_id}"
        )
        result.append(BotCommand(command="panel", description="📦Панель поставщика"))
    return result


async def set_default_commands(bot: Bot):
    await bot.set_my_commands(def_commands, BotCommandScopeDefault())


async def set_developer_commands(bot: Bot):
    commands = def_commands
    commands.append(BotCommand(command="test", description="test"))
    await bot.set_my_commands(commands, BotCommandScopeChat(chat_id=5263751490))


async def update_users_commands(bot: Bot):
    db = Database()
    for user in await db.get_users_not_clients():
        try:
            await bot.set_my_commands(
                await get_commands_by_role(user),
                BotCommandScopeChat(chat_id=user.chat_id),
            )
        except Exception as e:
            bot_log.error(e)
            except_log.exception(e)


async def update_user_commands(bot: Bot, client: Clients):
    await bot.set_my_commands(
        await get_commands_by_role(client), BotCommandScopeChat(chat_id=client.user_id)
    )
