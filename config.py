import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
OPENROUTER_API_KEY: str = os.environ["OPENROUTER_API_KEY"]
DAILY_HOUR: int = int(os.getenv("DAILY_HOUR", "9"))
DAILY_MINUTE: int = int(os.getenv("DAILY_MINUTE", "0"))
