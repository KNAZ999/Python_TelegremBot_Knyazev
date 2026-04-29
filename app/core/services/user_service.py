from app.core.users.repositories import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession


class UserService:
    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)

    async def get_user_ids_for_role(self, role: str) -> list[int]:
        """Получает ID пользователей по роли. Пока только 'waiter'"""
        if role == "waiter":
            return await self.repo.get_waiter_user_ids()
        return []