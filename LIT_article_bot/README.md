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
    The bot will fetch 4 articles immediately, and then check for updates **every 20 minutes** (configurable in `.env`).

## 🛠 Admin & Keyword Management

The bot includes interactive commands for administrators (restricted to `ADMIN_ID`):

| Command           | Usage                 | Description                                       |
| :---------------- | :-------------------- | :------------------------------------------------ |
| `/status`         | `/status`             | View bot uptime, source count, and keyword count. |
| `/force_fetch`    | `/force_fetch`        | Trigger an immediate check for new articles.      |
| `/add_keyword`    | `/add_keyword GenAI`  | Add a new tracking keyword instantly.             |
| `/remove_keyword` | `/remove_keyword NFT` | Remove a tracking keyword.                        |
| `/list_keywords`  | `/list_keywords`      | Show all active keywords.                         |

## Code Logic & Functions

### `bot.py` (Main Entry Point)

- **`is_admin(user_id)`**: A security check to ensure `ADMIN_ID` authorization before executing sensitive commands.
- **`status_command(update, context)`**: Reports system health, uptime, source count, and active keywords to the admin.
- **`force_fetch_command(update, context)`**: Manually triggers `scheduled_job` to fetch articles immediately.
- **`list_keywords_command(update, context)`**: Displays all currently active tracking keywords.
- **`add_keyword_command(update, context)`**: Adds a new keyword to the dynamic tracking list.
- **`remove_keyword_command(update, context)`**: Removes a keyword from the dynamic tracking list.
- **`remove_article(update, context)`**: Callback handler that deletes a message when the "Remove ❌" button is clicked.
- **`process_and_send(context, articles, limit)`**: Core pipeline that filters duplicates/relevance, formats HTML, generates hashtags, attaches UI buttons, and sends messages.
- **`scheduled_job(context)`**: Periodic background task that checks for new articles published since the last run.
- **`startup_job(context)`**: One-time task that runs on boot to fetch recent unique articles (last 7 days) and populate the channel.

### `fetcher.py` (RSS Handling)

- **`RSSFetcher.fetch_updates(last_check_time)`**: Iterates through all configured RSS feeds, parses entries, handles errors, and returns a list of normalized article objects.
- **`RSSFetcher._get_published_time(entry)`**: Helper that attempts to parse various date formats (published/updated) from RSS entries.

### `processor.py` (NLP & Formatting)

- **`ArticleProcessor.is_relevant(article, keywords)`**: Scans article titles and summaries for matches against the active keyword list.
- **`ArticleProcessor.process_article(article, keywords)`**: Classifies articles into categories (e.g., AI, Crypto), generates relevant hashtags, assigns a category tag, and sanitizes/truncates the summary.

### `storage.py` (Persistence)

- **`Storage.load_history()` / `save_history()`**: Handles reading and writing the list of sent article links to `history.json`.
- **`Storage.is_new(link)`**: Checks if a URL has already been processed to prevent duplicates.
- **`Storage.add_article(link)`**: Marks a URL as processed and updates the history file (capped at 1000 entries).
- **`Storage.load_keywords()` / `save_keywords()`**: Handles reading and writing dynamic keywords to `keywords.json`.
- **`Storage.add_keyword(keyword)` / `remove_keyword(keyword)`**: CRUD operations for managing the persistent keyword list.
