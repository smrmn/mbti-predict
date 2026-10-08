from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from services.swap_watch import (
    fetch_quote,
    get_state,
    is_owner,
    other,
    parse_asset,
    record_purchase,
    remember_owner,
    status_text,
    swap_keyboard,
)

router = Router()


@router.message(Command("swap"))
async def cmd_swap(message: Message) -> None:
    # Позиция личная: только владельцу. Его же чат запоминаем для уведомлений
    if not is_owner(message.from_user):
        return
    remember_owner(message.chat.id)
    state = get_state()
    try:
        q = fetch_quote(state)
    except Exception:
        await message.answer("Не удалось получить курс, попробуй позже")
        return
    await message.answer(status_text(state, q), parse_mode="HTML", reply_markup=swap_keyboard(state))


@router.message(Command("bought"))
async def cmd_bought(message: Message, command: CommandObject) -> None:
    if not is_owner(message.from_user):
        return
    remember_owner(message.chat.id)

    state = get_state()
    need = other(state["asset"])
    usage = f"Напиши, сколько получил: /bought 0.2951 {need}"
    parts = (command.args or "").split()
    if len(parts) != 2:
        await message.answer(usage)
        return
    try:
        amount = float(parts[0].replace(",", "."))
    except ValueError:
        await message.answer(usage)
        return
    asset = parse_asset(parts[1])
    if amount <= 0 or asset is None:
        await message.answer(usage)
        return
    if asset != need:
        await message.answer(f"Сейчас на руках {state['asset']}, купить можно только {need}.\n{usage}")
        return

    old, new = record_purchase(amount, asset)
    diff = (amount / old["base"] - 1) * 100
    await message.answer(
        f"Записал: {old['amount']:g} {old['asset']} → <b>{amount:g} {asset}</b>\n"
        f"Против прошлых {old['base']:g} {asset}: {diff:+.2f}%\n\n"
        f"Теперь слушаю {amount:g} {asset} / {new['base']:g} {old['asset']}: "
        f"напишу, когда за {asset} дадут больше {old['asset']}",
        parse_mode="HTML",
    )
