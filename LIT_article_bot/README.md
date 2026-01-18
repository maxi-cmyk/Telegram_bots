# Tech Law Telegram Bot

A Telegram bot that fetches relevant articles about tech and how it affects law (AI, Copyright, etc.), summarizes them using Google Gemini, and sends them to a channel.

## Setup

1.  **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

    _(Note: Create a requirements.txt if not exists, or just install `python-telegram-bot feedparser schedule requests google-generativeai python-dotenv`)_

2.  **Configuration**:
    - Rename `.env.example` to `.env`.
    - Add your `TELEGRAM_BOT_TOKEN`, `GOOGLE_API_KEY`, and `CHANNEL_ID`.

3.  **Run**:
    ```bash
    python bot.py
    ```
