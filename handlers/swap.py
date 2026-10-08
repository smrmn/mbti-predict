from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import config
from services.swap_watch import fetch_eth_wbtc_rate, status_text

router = Router()


@router.message(Command("swap"))
async def cmd_swap(message: Message) -> None:
    # Позиция личная: показываем только тому, кому шлём уведомления
    if message.from_user.id != config.SWAP_CHAT_ID:
        return
    try:
        rate = fetch_eth_wbtc_rate()
    except Exception:
        await message.answer("Не удалось получить курс, попробуй позже")
        return
    await message.answer(status_text(rate), parse_mode="HTML")
