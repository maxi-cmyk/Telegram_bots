# Tech Law Telegram Bot

## Features

- **Smart Fetching**: Fetches articles from tech/law RSS feeds (including Singapore Law Watch & Legal Advice).
- **AI Power**: Summarizes articles and generates hashtags using Google Gemini.
- **Deduplication**: Remembers sent articles so you don't get duplicates (persistent `history.json`).
- **Startup Fetch**: Immediately finds 4 fresh articles when you restart the bot.
- **Interactive**: Includes a "Remove ❌" button to delete unwanted messages.

## Setup

1.  **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

    _(Note: We use `python-telegram-bot[job-queue]` for scheduling)_

2.  **Configuration**:
    - Rename `.env.example` to `.env` (if you haven't already).
    - Add your `TELEGRAM_BOT_TOKEN`, `GOOGLE_API_KEY`, and `CHANNEL_ID`.
    - Ensure `CHANNEL_ID` starts with `-100` if it's a private channel (e.g., `-100123456789`).

3.  **Run**:
    ```bash
    python bot.py
    ```
    The bot will fetch 4 articles immediately, and then check for updates **every 60 minutes** (configurable in `.env`).
