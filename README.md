# Freshdesk Smart Scraper & Telegram Bot 🤖

A powerful Python tool to scrape Freshdesk tickets, fetching **full conversation history** (replies & private notes) which is often missing from standard exports. It includes an **AI Agent** mode to filter tickets by user intent and a **Telegram Bot** interface for easy mobile access.

## 🚀 Features

*   **Deep Scraping**: Fetches the entire conversation thread for every ticket.
*   **Smart Filtering (AI)**: Use LLMs (Gemini/OpenAI) to analyze tickets and determine if they match a specific intent (e.g., "Find users angry about login bugs").
*   **Date Filters**: Search for tickets within specific date ranges.
*   **Telegram Integration**: Chat with the bot to generate and download Excel reports directly on Telegram.
*   **Railway Ready**: Includes `Procfile` for one-click deployment to Railway.

## 🛠️ Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/DecentralizedJM/freshdesk-python-scraper.git
    cd freshdesk-python-scraper
    ```

2.  **Install Dependencies**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configuration**:
    Create a `.env` file in the root directory:
    ```ini
    FRESHDESK_DOMAIN=yourcompany.freshdesk.com
    FRESHDESK_API_KEY=your_freshdesk_api_key
    
    # Optional: For AI Filtering
    GEMINI_API_KEY=your_gemini_key
    # OR
    OPENAI_API_KEY=your_openai_key
    
    # Optional: For Telegram Bot
    TELEGRAM_BOT_TOKEN=your_telegram_bot_token
    ```

## 📖 Usage

### Option 1: CLI (Command Line)
Run the script interactively:
```bash
python main.py
```
It will ask for:
*   Keyword (e.g., "Refund")
*   Date Range (Optional)
*   Intent (Optional, e.g., "Find high priority billing issues")

### Option 2: Telegram Bot
Start the bot:
```bash
python telegram_bot.py
```
*   Open your bot in Telegram.
*   Send `/start`.
*   Follow the prompts to get your Excel report.

## ☁️ Deployment (Railway)

This project is configured for [Railway](https://railway.app).

1.  Fork/Push this repo to your GitHub.
2.  Create a New Project on Railway from your GitHub repo.
3.  Add the Environment Variables (`FRESHDESK_DOMAIN`, `API_KEY`, `TELEGRAM_BOT_TOKEN`, etc.) in Railway settings.
4.  Railway will detect the `Procfile` and start the Worker automatically.

## 📝 License
MIT
