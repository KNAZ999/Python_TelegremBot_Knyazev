from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker, AsyncSession


class Database:
    def __init__(self, dsn, base):
        # Преобразуем SecretStr в строку
        dsn_str = dsn.get_secret_value() if hasattr(dsn, 'get_secret_value') else str(dsn)
        self._engine: AsyncEngine = create_async_engine(dsn_str, echo=False)
        self._async_session = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )
        self.Base = base

    async def create_tables(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(self.Base.metadata.create_all)

    async def drop_tables(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(self.Base.metadata.drop_all)

    async def shutdown(self) -> None:
        """Закрываем engine — освобождаем соединения с БД"""
        if self._engine:
            await self._engine.dispose()