import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import telegram_bot  # Import the module to test

class TestTelegramBot(unittest.IsolatedAsyncioTestCase):
    async def test_start_command(self):
        # Mock Update and Context
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        
        # Call start
        state = await telegram_bot.start(update, context)
        
        # Verify
        self.assertEqual(state, telegram_bot.KEYWORD)
        update.message.reply_text.assert_called_once()
        print("Test Bot Start: SUCCESS")

    async def test_keyword_handler(self):
        update = MagicMock()
        update.message.text = "refund"
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.user_data = {}
        
        state = await telegram_bot.keyword_handler(update, context)
        
        self.assertEqual(state, telegram_bot.DATES)
        self.assertEqual(context.user_data['keyword'], 'refund')
        print("Test Keyword Handler: SUCCESS")

if __name__ == '__main__':
    unittest.main()
