from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
OPENROUTER_API_KEY: str = os.environ["OPENROUTER_API_KEY"]
DAILY_HOUR: int = int(os.getenv("DAILY_HOUR", "9"))
DAILY_MINUTE: int = int(os.getenv("DAILY_MINUTE", "0"))
PROXY: str | None = os.getenv("PROXY")

# Слежение за обменом ETH ↔ WBTC. Без SWAP_OWNER выключено.
# ID по @username Bot API не отдаёт: бот запоминает его, когда владелец пишет /swap
SWAP_OWNER: str = os.getenv("SWAP_OWNER", "").lstrip("@").lower()
# Стартовая позиция; после первой /bought позиция живёт в SWAP_STATE_FILE
SWAP_ETH_AMOUNT: float = float(os.getenv("SWAP_ETH_AMOUNT", "0"))
SWAP_WBTC_BASE: float = float(os.getenv("SWAP_WBTC_BASE", "0"))
SWAP_GAIN_PCT: float = float(os.getenv("SWAP_GAIN_PCT", "2"))
SWAP_TRAIL_PCT: float = float(os.getenv("SWAP_TRAIL_PCT", "1"))
# Комиссия кошелька за обмен: MetaMask Swaps — 0.875%, напрямую через агрегатор — 0
SWAP_FEE_PCT: float = float(os.getenv("SWAP_FEE_PCT", "0.875"))
# Сколько ETH не трогать в кнопке обмена ETH → WBTC: на газ
SWAP_GAS_RESERVE_ETH: float = float(os.getenv("SWAP_GAS_RESERVE_ETH", "0.005"))
SWAP_CHECK_MINUTES: int = int(os.getenv("SWAP_CHECK_MINUTES", "5"))
SWAP_STATE_FILE: str = os.getenv("SWAP_STATE_FILE", "swap_watch.json")
