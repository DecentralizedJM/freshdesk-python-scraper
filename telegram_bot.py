import logging
import os
import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, ConversationHandler, filters
from config import TELEGRAM_BOT_TOKEN, FRESHDESK_DOMAIN, FRESHDESK_API_KEY
from freshdesk_client import FreshdeskClient
from report_generator import generate_report
from ai_processor import TicketAnalyzer

# Enable logging; suppress httpx/httplib INFO so token isn't logged in request URLs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# State Definitions
KEYWORD, DATES, INTENT = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! I am your Freshdesk Bot.\n\n"
        "I can help you scrape tickets and analyze them with AI.\n"
        "Let's start! \n\n"
        "📥 **Enter the Keyword** you want to search for:"
    )
    return KEYWORD

async def keyword_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    context.user_data['keyword'] = user_input
    
    await update.message.reply_text(
        f"✅ Keyword set to: '{user_input}'\n\n"
        "📅 **Enter Date Range** (YYYY-MM-DD to YYYY-MM-DD)\n"
        "Example: `2023-01-01 to 2023-02-01`\n"
        "Or type 'skip' to search all time."
    )
    return DATES

async def dates_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    start_date = None
    end_date = None
    
    if user_input.lower() != 'skip':
        parts = user_input.split(' to ')
        if len(parts) == 2:
            start_date = parts[0].strip()
            end_date = parts[1].strip()
        else:
            await update.message.reply_text("⚠️ Invalid format. Please use 'YYYY-MM-DD to YYYY-MM-DD' or type 'skip'. Try again:")
            return DATES

    context.user_data['start_date'] = start_date
    context.user_data['end_date'] = end_date
    
    await update.message.reply_text(
        "🧠 **Enter User Intent** for AI Analysis.\n"
        "Example: 'Find users asking about login bugs'\n"
        "Or type 'skip' for no specific intent."
    )
    return INTENT

async def intent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    intent = user_input if user_input.lower() != 'skip' else ""
    context.user_data['intent'] = intent
    
    # Notify user process has started
    await update.message.reply_text(
        "⏳ **Processing...**\n"
        "Searching tickets, fetching conversations, and running AI analysis.\n"
        "This may take a minute. Please wait."
    )
    
    # Run the blocking scraping logic in a separate thread/executor to not block the bot
    # We pass the collected data to a helper function
    try:
        # NOTE: In a high-scale prod app, use proper worker queues (Celery/Redis).
        # For this tool, running in an executor is sufficient.
        loop = asyncio.get_running_loop()
        file_path = await loop.run_in_executor(None, run_scraper_logic, context.user_data)
        
        if file_path:
            await update.message.reply_document(document=open(file_path, 'rb'), filename=os.path.basename(file_path))
            await update.message.reply_text("✅ Done! Here is your report.")
            os.remove(file_path) # Cleanup
        else:
            await update.message.reply_text("❌ No tickets found matching your criteria.")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ An error occurred: {str(e)}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operation cancelled. Type /start to try again.")
    return ConversationHandler.END

# --- Helper Wrapper for Blocking Code ---
import asyncio

def run_scraper_logic(data):
    keyword = data['keyword']
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    intent = data.get('intent')
    
    # Init Logic
    client = FreshdeskClient(FRESHDESK_DOMAIN, FRESHDESK_API_KEY)
    ai = TicketAnalyzer()
    
    found_tickets = client.search_tickets(keyword, start_date, end_date)
    if not found_tickets:
        return None
        
    detailed_tickets = []
    for ticket in found_tickets:
        t_id = ticket['id']
        full_ticket = client.get_ticket_details(t_id)
        
        if full_ticket:
            # AI Analysis
            combined_text = f"Subject: {full_ticket.get('subject')}\nDesc: {full_ticket.get('description_text')}\n"
            is_relevant, summary = ai.analyze(combined_text, intent)
            full_ticket['ai_relevant'] = is_relevant
            full_ticket['ai_summary'] = summary
            
            detailed_tickets.append(full_ticket)
            
    # Report
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_kw = "".join([c for c in keyword if c.isalnum()])
    filename = f"report_{clean_kw}_{timestamp}.xlsx"
    generate_report(detailed_tickets, filename=filename)
    
    return filename

if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN is missing.")
        exit(1)
        
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            KEYWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, keyword_handler)],
            DATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, dates_handler)],
            INTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, intent_handler)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(conv_handler)
    
    print("Bot is polling (use webhooks in production for lower latency)...")
    application.run_polling()
