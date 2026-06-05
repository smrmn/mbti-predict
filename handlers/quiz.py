from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services.mbti_quiz import QUESTIONS, calculate_mbti, get_description
from storage.profiles import save_profile

router = Router()


class QuizStates(StatesGroup):
    answering = State()


def _make_keyboard(question_index: int) -> InlineKeyboardMarkup:
    q = QUESTIONS[question_index]
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"A — {q['a']}", callback_data=f"quiz:a:{question_index}"),
        ],
        [
            InlineKeyboardButton(text=f"B — {q['b']}", callback_data=f"quiz:b:{question_index}"),
        ],
    ])


async def start_quiz(message: Message, state: FSMContext) -> None:
    """Запустить тест — вызывается из handlers/start.py."""
    await state.set_state(QuizStates.answering)
    await state.update_data(answers=[], current=0)
    await _send_question(message, 0)


async def _send_question(target: Message | CallbackQuery, index: int) -> None:
    q = QUESTIONS[index]
    text = f"<b>Вопрос {index + 1} / {len(QUESTIONS)}</b>\n\n{q['text']}"
    kb = _make_keyboard(index)

    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        # CallbackQuery — редактируем текущее сообщение
        await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(QuizStates.answering, F.data.startswith("quiz:"))
async def handle_answer(callback: CallbackQuery, state: FSMContext) -> None:
    _, choice, idx_str = callback.data.split(":")
    idx = int(idx_str)

    data = await state.get_data()
    answers: list[str] = data.get("answers", [])
    current: int = data.get("current", 0)

    # Защита от повторного нажатия старой кнопки
    if idx != current:
        await callback.answer("Этот вопрос уже позади 😊")
        return

    answers.append(choice)
    next_idx = current + 1

    if next_idx < len(QUESTIONS):
        await state.update_data(answers=answers, current=next_idx)
        await callback.answer()
        await _send_question(callback, next_idx)
    else:
        # Тест завершён
        await state.clear()
        mbti = calculate_mbti(answers)
        description = get_description(mbti)
        save_profile(callback.from_user.id, mbti)

        await callback.message.edit_text(
            f"✅ <b>Тест завершён!</b>\n\n"
            f"Твой тип: <b>{mbti}</b>\n"
            f"{description}\n\n"
            f"Каждый день я буду присылать тебе персональное предсказание 🔮\n"
            f"Хочешь получить первое прямо сейчас? Напиши /predict",
            parse_mode="HTML",
        )
        await callback.answer()
