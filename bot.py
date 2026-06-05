import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

import config
from handlers import start, quiz
from services.scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    session = AiohttpSession(proxy=config.PROXY) if config.PROXY else AiohttpSession()
    bot = Bot(token=config.BOT_TOKEN, session=session)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(quiz.router)

    setup_scheduler(bot)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
