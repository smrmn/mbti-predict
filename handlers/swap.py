from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from services.swap_watch import fetch_eth_wbtc_rate, is_owner, remember_owner, status_text

router = Router()


@router.message(Command("swap"))
async def cmd_swap(message: Message) -> None:
    # Позиция личная: только владельцу. Его же чат запоминаем для уведомлений
    if not is_owner(message.from_user):
        return
    remember_owner(message.chat.id)
    try:
        rate = fetch_eth_wbtc_rate()
    except Exception:
        await message.answer("Не удалось получить курс, попробуй позже")
        return
    await message.answer(status_text(rate), parse_mode="HTML")
