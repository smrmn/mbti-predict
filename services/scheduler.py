import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

import config
from storage.profiles import get_all_users
from services.prediction import get_prediction

logger = logging.getLogger(__name__)


async def send_daily_predictions(bot: Bot) -> None:
    """Рассылает предсказания всем зарегистрированным пользователям."""
    users = get_all_users()
    logger.info(f"Рассылка предсказаний: {len(users)} пользователей")

    for user in users:
        try:
            prediction = get_prediction(user["mbti"])
            await bot.send_message(chat_id=user["user_id"], text=prediction)
        except Exception as e:
            logger.error(f"Ошибка при отправке пользователю {user['user_id']}: {e}")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Создаёт и запускает планировщик ежедневной рассылки."""
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        send_daily_predictions,
        trigger="cron",
        hour=config.DAILY_HOUR,
        minute=config.DAILY_MINUTE,
        kwargs={"bot": bot},
    )
    scheduler.start()
    logger.info(f"Планировщик запущен: рассылка в {config.DAILY_HOUR:02d}:{config.DAILY_MINUTE:02d} МСК")
    return scheduler
