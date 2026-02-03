import os
from dotenv import load_dotenv

load_dotenv()

FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")
FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not FRESHDESK_DOMAIN or not FRESHDESK_API_KEY:
    print("Warning: FRESHDESK_DOMAIN or FRESHDESK_API_KEY not found in .env file.")
    
if not GEMINI_API_KEY and not OPENAI_API_KEY:
    print("Note: No AI API keys found. 'Intent' filtering will use keyword matching.")

if not TELEGRAM_BOT_TOKEN:
    print("Warning: TELEGRAM_BOT_TOKEN not found for bot execution.")
