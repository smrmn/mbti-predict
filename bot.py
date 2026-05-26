import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import config
from handlers import start, quiz

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров (порядок важен)
    dp.include_router(start.router)
    dp.include_router(quiz.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
