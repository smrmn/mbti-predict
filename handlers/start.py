from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext

from storage.profiles import get_profile
from handlers.quiz import start_quiz

router = Router()


def _start_test_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧩 Пройти тест", callback_data="begin_quiz")]
    ])


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    profile = get_profile(message.from_user.id)

    if profile:
        mbti = profile["mbti"]
        await message.answer(
            f"С возвращением! 👋\n\n"
            f"Твой MBTI-тип: <b>{mbti}</b>\n\n"
            f"Каждый день в 9:00 я присылаю тебе персональное предсказание 🔮\n"
            f"Хочешь получить его прямо сейчас? /predict\n"
            f"Или перепройди тест: /test",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "Привет! 👋 Я <b>MBTI Predict</b> — бот, который каждый день присылает "
            "персональное предсказание, основанное на твоём психологическом типе.\n\n"
            "Для начала давай определим твой MBTI-тип. "
            "Тебя ждут 16 вопросов с вариантами ответов — это займёт пару минут 🙂",
            reply_markup=_start_test_keyboard(),
            parse_mode="HTML",
        )


@router.callback_query(lambda c: c.data == "begin_quiz")
async def begin_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.delete()
    await start_quiz(callback.message, state)
    await callback.answer()


@router.message(Command("test"))
async def cmd_test(message: Message, state: FSMContext) -> None:
    await message.answer("Начинаем заново! Отвечай честно 😊")
    await start_quiz(message, state)


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    profile = get_profile(message.from_user.id)
    if not profile:
        await message.answer(
            "У тебя пока нет профиля. Пройди тест: /start"
        )
    else:
        mbti = profile["mbti"]
        since = profile.get("registered_at", "неизвестно")
        await message.answer(
            f"👤 Твой профиль\n\n"
            f"MBTI-тип: <b>{mbti}</b>\n"
            f"Тест пройден: {since}\n\n"
            f"Хочешь перепройти? /test",
            parse_mode="HTML",
        )
