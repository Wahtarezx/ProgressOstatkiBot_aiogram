from core.database.query_BOT import Database
from core.database.model_logs import LogsTTN
from sqlalchemy import text, delete, update, func
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload


class DBLogs(Database):
    def __init__(self):
        super().__init__()

    async def count_accept_ttns(self, shopcode: str | int) -> int:
        async with self.AsyncSession() as session:
            q = await session.execute(
                select(func.count())
                .select_from(LogsTTN)
                .where(
                    LogsTTN.cash_number == shopcode,
                    LogsTTN.level == "SUCCES",
                    LogsTTN.type == "Подтвердить",
                )
            )
            return q.scalar()


async def test():
    db_logs = DBLogs()
    print(await db_logs.count_accept_ttns(123))


if __name__ == "__main__":
    import asyncio

    asyncio.run(test())
