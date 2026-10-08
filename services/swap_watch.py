from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import date

import requests
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config

logger = logging.getLogger(__name__)

PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
ASSETS = ("ETH", "WBTC")

# Фазы слежения:
#   idle  — ждём, пока выгода дойдёт до порога SWAP_GAIN_PCT;
#   armed — порог пройден, копим пик и ждём отката на SWAP_TRAIL_PCT п.п.
#           или возврата к порогу, проверяем чаще;
#   fired — сообщение отправлено, молчим, пока выгода не уйдёт ниже порога.
IDLE, ARMED, FIRED = "idle", "armed", "fired"

_last_check = 0.0


KYBER_URL = "https://aggregator-api.kyberswap.com/ethereum/api/v1/routes"
# Адреса в Ethereum mainnet и знаки после запятой
TOKENS = {
    "ETH": ("0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", 18),
    "WBTC": ("0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", 8),
}


# Экран обмена в MetaMask Mobile: handleSwapUrl в MetaMask/metamask-mobile.
# from/to — CAIP-19, amount — в минимальных единицах; работает без подписи ссылки
METAMASK_SWAP_URL = "https://link.metamask.io/swap"
CAIP = {
    "ETH": "eip155:1/slip44:60",
    "WBTC": "eip155:1/erc20:0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
}


@dataclass
class Quote:
    """Сколько другой валюты выйдет за позицию целиком."""
    market: float  # по рыночному курсу
    dex: float     # котировка агрегатора на эту сумму (с проскальзыванием)
    gas: float     # газ, в получаемой валюте
    net: float     # на кошелёк: dex − комиссия кошелька − газ
    rate: float    # рыночный курс ETH/WBTC
    source: str    # "kyber" или "coingecko", если агрегатор не ответил


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


def _kyber_quote(amount: float, asset: str) -> Quote:
    token_in, dec_in = TOKENS[asset]
    token_out, dec_out = TOKENS[other(asset)]
    response = requests.get(
        KYBER_URL,
        params={"tokenIn": token_in, "tokenOut": token_out, "amountIn": str(round(amount * 10**dec_in))},
        headers={"x-client-id": "mbti-predict"},
        timeout=15,
    )
    response.raise_for_status()
    route = response.json()["data"]["routeSummary"]

    dex = int(route["amountOut"]) / 10**dec_out
    price_in = float(route["amountInUsd"]) / amount  # рыночные цены агрегатора, USD за единицу
    price_out = float(route["amountOutUsd"]) / dex
    gas = float(route["gasUsd"]) / price_out
    rate = price_in / price_out if asset == "ETH" else price_out / price_in
    return Quote(
        market=amount * price_in / price_out,
        dex=dex,
        gas=gas,
        net=dex * (1 - config.SWAP_FEE_PCT / 100) - gas,
        rate=rate,
        source="kyber",
    )


def fetch_quote(state: dict) -> Quote:
    """Котировка обмена всей позиции; агрегатор недоступен — рынок CoinGecko без газа."""
    try:
        return _kyber_quote(state["amount"], state["asset"])
    except Exception as e:
        logger.warning(f"KyberSwap не ответил, беру CoinGecko: {e}")
    rate = fetch_eth_wbtc_rate()
    market = convert(state["amount"], state["asset"], rate)
    return Quote(market, market, 0.0, market * (1 - config.SWAP_FEE_PCT / 100), rate, "coingecko")


def other(asset: str) -> str:
    return "WBTC" if asset == "ETH" else "ETH"


def parse_asset(text: str) -> str | None:
    text = text.upper()
    if text in ("BTC", "WBTC"):
        return "WBTC"
    return "ETH" if text == "ETH" else None


def convert(amount: float, asset: str, rate: float) -> float:
    """Сколько другой валюты выйдет за amount asset по курсу ETH/WBTC."""
    return amount * rate if asset == "ETH" else amount / rate


def gain_pct(state: dict, out: float) -> float:
    """Насколько больше другой валюты выйдет, чем за неё отдали, в %."""
    return (out / state["base"] - 1) * 100


def step(state: dict, gain: float) -> str | None:
    """Двигает фазу по новой выгоде. Возвращает "trail" или "floor", если пора писать."""
    threshold, trail = config.SWAP_GAIN_PCT, config.SWAP_TRAIL_PCT
    phase = state["phase"]

    if phase == IDLE:
        if gain >= threshold:
            state.update(phase=ARMED, peak=gain)
        return None

    if phase == ARMED:
        state["peak"] = max(state["peak"], gain)
        if gain < threshold:
            state["phase"] = FIRED
            return "floor"
        if state["peak"] - gain >= trail:
            state["phase"] = FIRED
            return "trail"
        return None

    # FIRED: заново взводимся только после ухода ниже порога
    if gain < threshold:
        state.update(phase=IDLE, peak=None)
    return None


def _pair(state: dict) -> str:
    return f"{state['asset']} → {other(state['asset'])}"


def _money_line(state: dict, q: Quote) -> str:
    """Главное: сколько придёт на кошелёк и выгода."""
    return (
        f"💰 <b>{q.net:.5f} {other(state['asset'])}</b> на кошелёк "
        f"(<b>{gain_pct(state, q.net):+.2f}%</b>)"
    )


def _position_line(state: dict) -> str:
    return f"за {state['amount']:g} {state['asset']} · было {state['base']:g} {other(state['asset'])}"


def _fallback_line(q: Quote) -> list[str]:
    return [] if q.source == "kyber" else ["<i>без газа: агрегатор не ответил</i>"]


def swap_keyboard(state: dict) -> InlineKeyboardMarkup:
    """Кнопка, открывающая обмен всей позиции в MetaMask; подтверждает владелец."""
    asset = state["asset"]
    amount = state["amount"]
    if asset == "ETH":
        amount -= config.SWAP_GAS_RESERVE_ETH  # иначе нечем платить за газ
    dec = TOKENS[asset][1]
    url = (
        f"{METAMASK_SWAP_URL}?from={CAIP[asset]}&to={CAIP[other(asset)]}"
        f"&amount={max(round(amount * 10**dec), 0)}"
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🦊 Обменять {_pair(state)} в MetaMask", url=url)]
    ])


def status_text(state: dict, q: Quote) -> str:
    """Текущее положение: сколько придёт на кошелёк и фаза слежения."""
    base, to = state["base"], other(state["asset"])
    threshold = config.SWAP_GAIN_PCT
    if state["phase"] == IDLE:
        phase = f"Жду +{threshold:g}%: {base * (1 + threshold / 100):.5f} {to}"
    elif state["phase"] == ARMED:
        phase = (
            f"Пик {state['peak']:+.2f}%, напишу при откате до "
            f"{state['peak'] - config.SWAP_TRAIL_PCT:+.2f}% или спуске ниже +{threshold:g}%"
        )
    else:
        phase = f"Уже написал, снова — после спуска ниже +{threshold:g}%"
    return "\n".join([_money_line(state, q), _position_line(state), phase] + _fallback_line(q))


def alert_text(kind: str, state: dict, q: Quote) -> str:
    if kind == "trail":
        head = f"🔔 <b>{_pair(state)}: откат от пика</b>"
    else:
        head = f"⚠️ <b>{_pair(state)}: спуск к порогу +{config.SWAP_GAIN_PCT:g}%</b>"
    return "\n".join(
        [head, _money_line(state, q), f"Пик был {state['peak']:+.2f}%", _position_line(state)]
        + _fallback_line(q)
    )


def _load_state() -> dict:
    # Позиция до первой /bought — из окружения: ETH на руках, отданные за них WBTC
    state = {
        "chat_id": None,
        "asset": "ETH",
        "amount": config.SWAP_ETH_AMOUNT,
        "base": config.SWAP_WBTC_BASE,
        "phase": IDLE,
        "peak": None,
    }
    try:
        with open(config.SWAP_STATE_FILE, encoding="utf-8") as f:
            state.update(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    state.pop("notified", None)  # поле версии 0.5
    return state


def _save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(config.SWAP_STATE_FILE)), exist_ok=True)
    with open(config.SWAP_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def get_state() -> dict:
    return _load_state()


def is_owner(user) -> bool:
    return bool(config.SWAP_OWNER) and (user.username or "").lower() == config.SWAP_OWNER


def remember_owner(chat_id: int) -> None:
    state = _load_state()
    if state["chat_id"] != chat_id:
        state["chat_id"] = chat_id
        _save_state(state)
        logger.info("Слежение ETH ↔ WBTC: запомнил чат владельца")


def record_purchase(amount: float, asset: str) -> tuple[dict, dict]:
    """Обмен сделан: купили amount asset за всё, что было на руках. Слежение — в обратную сторону."""
    old = _load_state()
    history = old.get("history", []) + [
        {"date": str(date.today()), "sold": old["amount"], "sold_asset": old["asset"],
         "bought": amount, "bought_asset": asset}
    ]
    new = dict(old, asset=asset, amount=amount, base=old["amount"], phase=IDLE, peak=None, history=history)
    _save_state(new)
    logger.info(f"Слежение ETH ↔ WBTC: куплено {amount:g} {asset}")
    return old, new


async def check_swap(bot: Bot) -> None:
    """Раз в минуту; вне взвода — не чаще SWAP_CHECK_MINUTES."""
    global _last_check
    state = _load_state()
    if not state["chat_id"]:
        return  # владелец ещё не писал /swap — слать некуда
    if state["phase"] != ARMED and time.monotonic() - _last_check < config.SWAP_CHECK_MINUTES * 60 - 5:
        return
    _last_check = time.monotonic()

    try:
        q = fetch_quote(state)
    except Exception as e:
        logger.warning(f"Не удалось получить курс ETH/WBTC: {e}")
        return

    before = dict(state)
    kind = step(state, gain_pct(state, q.net))
    if kind:
        await bot.send_message(
            chat_id=state["chat_id"], text=alert_text(kind, state, q), parse_mode="HTML",
            reply_markup=swap_keyboard(state),
        )
        logger.info(f"Слежение {_pair(state)}: {kind}, пик {state['peak']:+.2f}%")
    if state != before:
        _save_state(state)
