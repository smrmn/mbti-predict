from __future__ import annotations

import json
import os
from datetime import date

PROFILES_DIR = os.path.join(os.path.dirname(__file__), "..", "profiles")


def _path(user_id: int) -> str:
    os.makedirs(PROFILES_DIR, exist_ok=True)
    return os.path.join(PROFILES_DIR, f"{user_id}.json")


def save_profile(user_id: int, mbti: str) -> None:
    """Сохранить (или перезаписать) MBTI-тип пользователя."""
    data = {
        "mbti": mbti,
        "registered_at": str(date.today()),
    }
    with open(_path(user_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_profile(user_id: int) -> dict | None:
    """Вернуть профиль пользователя или None, если его нет."""
    p = _path(user_id)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def get_all_users() -> list[dict]:
    """Вернуть список всех профилей (для рассылки предсказаний)."""
    os.makedirs(PROFILES_DIR, exist_ok=True)
    users = []
    for filename in os.listdir(PROFILES_DIR):
        if filename.endswith(".json"):
            user_id = int(filename.removesuffix(".json"))
            with open(os.path.join(PROFILES_DIR, filename), encoding="utf-8") as f:
                data = json.load(f)
            users.append({"user_id": user_id, **data})
    return users
