from telegram.ext import ApplicationBuilder
from settings.config import AppSettings
from app.handlers import HANDLERS
import asyncio


def create_bot(settings: AppSettings):
    builder = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN)
    builder = builder.post_init(lambda app: print("Бот запущен"))
    application = builder.build()

    for handler_entry in HANDLERS:
        application.add_handler(handler_entry.handler)

    return application


async def main():
    settings = AppSettings()
    bot = create_bot(settings)
    await bot.run_polling()


if __name__ == "__main__":
    asyncio.run(main())