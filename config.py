from dotenv import load_dotenv
import os

load_dotenv()

api_keys = [
    os.getenv("OPENAI_API_KEY1"),
    os.getenv("OPENAI_API_KEY2"),
    os.getenv("OPENAI_API_KEY3"),
    os.getenv("OPENAI_API_KEY4")
]

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID'))
EXCLUDED_GUILD_IDS = os.getenv("EXCLUDED_GUILD_IDS", "").split(",")