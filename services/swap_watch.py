from __future__ import annotations

import json
import logging
import os

import requests
from aiogram import Bot

import config

logger = logging.getLogger(__name__)

PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"


def fetch_eth_wbtc_rate() -> float:
    """Сколько WBTC дают за 1 ETH по рыночным ценам CoinGecko."""
    response = requests.get(
        PRICE_URL,
        params={"ids": "ethereum,wrapped-bitcoin", "vs_currencies": "usd"},
        timeout=15,
    )
    response.raise_for_status()
    prices = response.json()
    return prices["ethereum"]["usd"] / prices["wrapped-bitcoin"]["usd"]


def target_wbtc() -> float:
    return config.SWAP_WBTC_BASE * (1 + config.SWAP_GAIN_PCT / 100)


def status_text(rate: float) -> str:
    """Текущее положение: сколько WBTC выйдет за ETH и сколько до цели."""
    wbtc_now = config.SWAP_ETH_AMOUNT * rate
    gain = (wbtc_now / config.SWAP_WBTC_BASE - 1) * 100
    target = target_wbtc()
    return (
        f"{config.SWAP_ETH_AMOUNT:g} ETH → <b>{wbtc_now:.5f} WBTC</b> "
        f"({gain:+.2f}% к {config.SWAP_WBTC_BASE:g})\n"
        f"Цель: {target:.5f} WBTC (+{config.SWAP_GAIN_PCT:g}%), "
        f"курс ETH/WBTC сейчас {rate:.6f}, нужен {target / config.SWAP_ETH_AMOUNT:.6f}"
    )


def _load_state() -> dict:
    try:
        with open(config.SWAP_STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"notified": False}


def _save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(config.SWAP_STATE_FILE)), exist_ok=True)
    with open(config.SWAP_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


async def check_swap(bot: Bot) -> None:
    """Уведомляет один раз при пересечении цели; снова — только после возврата ниже неё."""
    try:
        rate = fetch_eth_wbtc_rate()
    except Exception as e:
        logger.warning(f"Не удалось получить курс ETH/WBTC: {e}")
        return

    reached = config.SWAP_ETH_AMOUNT * rate >= target_wbtc()
    state = _load_state()

    if reached and not state["notified"]:
        await bot.send_message(
            chat_id=config.SWAP_CHAT_ID,
            text="🔔 ETH → WBTC: цель достигнута\n\n" + status_text(rate),
            parse_mode="HTML",
        )
        logger.info(f"ETH/WBTC: цель достигнута, курс {rate:.6f}")
    if reached != state["notified"]:
        _save_state({"notified": reached})
