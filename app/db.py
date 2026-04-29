from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncContextManager


class Database:
    def __init__(self, dsn: str, base: DeclarativeBase):
        # Создаём асинхронный движок
        self._engine: AsyncEngine = create_async_engine(dsn, echo=False)  # включите echo=True для отладки SQL

        # Фабрика сессий
        self._async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            class_=AsyncSession
        )

        # Сохраняем Base для создания таблиц
        self._base = base

    async def shutdown(self):
        """Закрывает все соединения"""
        await self._engine.dispose()

    async def create_tables(self):
        """Создаёт все таблицы, описанные в моделях"""
        async with self._engine.begin() as conn:
            await conn.run_sync(self._base.metadata.create_all)