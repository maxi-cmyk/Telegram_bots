# Tech Law Telegram Bot

## Features

- **Smart Fetching**: Fetches from trusted Tech/Law sources:
  - **Singapore**: Singapore Law Watch, Business Times Tech, Tech Revolutionist (Tech Explained), TechGoondu, Tech for Good Institute.
  - **International**: Artificial Lawyer, ABA Journal, Eric Goldman's Blog, MIT Tech Review, Berkeley Tech Law, EFF.
- **Classification**: Auto-tags articles into categories like `[Quantum Computing]`, `[Cryptography]`, `[AI & Law]`, `[Green Tech]` based on keywords.
- **Deduplication**: Remembers sent articles (persistent `history.json`) to avoid duplicates.
- **Startup Fetch**: Immediately finds 4 fresh articles when you restart the bot.
- **Interactive**: Includes a "Remove ❌" button to delete unwanted messages.

## Setup

1.  **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

    (Note: use `python-telegram-bot[job-queue]` for scheduling)

2.  **Configuration**:
    The bot is configured via environment variables and `config.py`.

    ### Environment Variables (`.env`)
    - `TELEGRAM_BOT_TOKEN`: Your API token.
    - `CHANNEL_ID`: The channel to post to (start with `-100`).
    - `CHECK_INTERVAL_MINUTES`: How often to check feeds (default: 60).
    - `ADMIN_ID`: (Optional) Your numerical Telegram User ID for admin commands.
    - `GOOGLE_API_KEY`: Your Google API key for specific features (e.g., custom search).

3.  **Run**:
    ```bash
    python bot.py
    ```
    The bot will fetch 4 articles immediately, and then check for updates **every 60 minutes** (configurable in `.env`).

## 🛠 Admin & Keyword Management

The bot includes interactive commands for administrators (restricted to `ADMIN_ID`):

| Command           | Usage                 | Description                                       |
| :---------------- | :-------------------- | :------------------------------------------------ |
| `/status`         | `/status`             | View bot uptime, source count, and keyword count. |
| `/force_fetch`    | `/force_fetch`        | Trigger an immediate check for new articles.      |
| `/add_keyword`    | `/add_keyword GenAI`  | Add a new tracking keyword instantly.             |
| `/remove_keyword` | `/remove_keyword NFT` | Remove a tracking keyword.                        |
| `/list_keywords`  | `/list_keywords`      | Show all active keywords.                         |

## Code Overview

### `bot.py`

- **`startup_job`**: Runs once on boot. Fetches 4 unique articles from the last 7 days to populate the channel immediately.
- **`scheduled_job`**: Runs periodically (default: every hour). Checks for _new_ articles published since the last check.
- **`process_and_send`**: The core logic. It filters duplicates (using `storage.py`), relevance (using `processor.py`), formats the message with HTML, attaches the "Remove" button, and sends it.
- **`remove_article`**: The callback handler that actually deletes the message when you click "Remove ❌".

### `fetcher.py`

- **`RSSFetcher.fetch_updates`**: parses the list of RSS feeds defined in `config.py`. It normalizes dates and handles errors (like bad feeds) gracefully.

### `processor.py`

- **`ArticleProcessor.process_article`**: Classifies articles into categories (e.g., Quantum, AI) based on keywords and generates hashtags. Uses the original RSS summary for the content.

### `storage.py`

- **`Storage`**: Manages `history.json`. It ensures we never spam the channel with the same article twice, even if the bot restarts.
