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
    - `ADMIN_IDS`: Users allowed to use admin commands (comma-separated, e.g., `12345,67890`).
    - `OLLAMA_MODEL`: Local AI model to use (default: `llama3.2`).

3.  **Run**:
    ```bash
    python bot.py
    ```
    The bot will fetch 4 articles immediately, and then check for updates **every 30 minutes** (configurable in `.env`).

## 🛠 Admin & Keyword Management

The bot includes interactive commands for administrators (restricted to `ADMIN_ID`):

| Command           | Usage                 | Description                                                   |
| :---------------- | :-------------------- | :------------------------------------------------------------ |
| `/status`         | `/status`             | View bot uptime, source count, and keyword count.             |
| `/force_fetch`    | `/force_fetch`        | Trigger an immediate check for new articles.                  |
| `/add_keyword`    | `/add_keyword GenAI`  | Add a new tracking keyword instantly.                         |
| `/remove_keyword` | `/remove_keyword NFT` | Remove a tracking keyword.                                    |
| `/list_keywords`  | `/list_keywords`      | Show all active keywords.                                     |
| `/share`          | `/share <url>`        | Manually scrape and share an article URL.                     |
| `/search`         | `/search <query>`     | Search past articles by **Title**, **Category**, or **Tags**. |

### 🔎 Search & Categories (DM the bot)

The bot automatically categorizes articles (e.g., "AI & Law", "Tech Policy") and adds tags.

- **Deep Search**: Finds keywords in titles, summaries, and even original URLs.
- **Search by Topic**: `/search AI` (Finds all AI-related articles)
- **Search by Category**: `/search Regulation`

### 📩 Private Utilities (DMs)

- **Summarize on Demand**: Send any article link to the bot in a **Private Message**. It will reply with an AI summary (without posting to the channel).

## Code Logic & Functions

### `bot.py` (Main Entry Point)

- **`is_admin(user_id)`**: A security check to ensure `ADMIN_ID` authorization before executing sensitive commands.
- **`status_command(update, context)`**: Reports system health, uptime, source count, and active keywords to the admin.
- **`force_fetch_command(update, context)`**: Manually triggers `scheduled_job` to fetch articles immediately.
- **`list_keywords_command(update, context)`**: Displays all currently active tracking keywords.
- **`add_keyword_command(update, context)`**: Adds a new keyword to the dynamic tracking list.
- **`remove_keyword_command(update, context)`**: Removes a keyword from the dynamic tracking list.
- **`remove_article(update, context)`**: Callback handler that deletes a message when the "Remove ❌" button is clicked.
- **Start Migration**: On first run, it automatically migrates existing `history.json` and `keywords.json` to `bot_data.db`.
- **`process_and_send`**: The core logic. It filters duplicates (using `storage.py`), relevance (using `processor.py`), formats the message with HTML, attaches the "Remove" button, and sends it.
- **`scheduled_job`**: Runs periodically (default: every hour). Checks for _new_ articles published since the last check.
- **`startup_job`**: Runs once on boot. Fetches 4 unique articles from the last 7 days to populate the channel immediately.

### `fetcher.py` (RSS Handling)

- **`RSSFetcher.fetch_updates(last_check_time)`**: Iterates through all configured RSS feeds, parses entries, handles errors, and returns a list of normalized article objects.
- **`RSSFetcher._get_published_time(entry)`**: Helper that attempts to parse various date formats (published/updated) from RSS entries.

### `processor.py` (NLP & Formatting)

- **`ArticleProcessor.is_relevant(article, keywords)`**: Scans article titles and summaries for matches against the active keyword list.
- **`ArticleProcessor.process_article(article, keywords)`**: Classifies articles into categories (e.g., AI, Crypto), generates relevant hashtags, assigns a category tag, and sanitizes/truncates the summary.

### `storage.py` (Persistence)

- **`Storage` (SQLite Migrated)**: Manages `bot_data.db`. Handles persistent history and active keywords using SQLite for robustness and thread safety.
- **`_run_migration()`**: Automatically imports legacy `history.json` and `keywords.json` data into the database on first run.
- **`is_new(link)` / `add_article(link)`**: Checks and adds articles using efficient SQL queries.
- **`get_keywords()` / `add_keyword()`**: Manages dynamic keyword filtering via the database table.
