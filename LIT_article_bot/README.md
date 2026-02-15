# Tech Law Telegram Bot

A sophisticated Telegram bot that fetches, categorizes, and summarizes technology law news from Singapore and international sources. It features a RAG (Retrieval-Augmented Generation) engine to answer questions based on the articles it has collected.

## Features

- **Smart Fetching**:
  - **RSS Feeds**: Singapore Law Watch, Business Times Tech, Tech Revolutionist, TechGoondu, Tech for Good Institute, Artificial Lawyer, ABA Journal, Eric Goldman's Blog, MIT Tech Review, Berkeley Tech Law, EFF.
  - **Custom Scrapers**: Handles sites without RSS feeds, such as the **PDPC Press Room**.
- **RAG Engine**:
  - Indexes all fetched articles into a local vector database (**ChromaDB**).
  - Allows users to ask questions (`/ask`) and get answers grounded in the actual news content using **Ollama**.
- **Classification**: Auto-tags articles (e.g., `[Quantum Computing]`, `[AI & Law]`) based on content analysis.
- **SQLite Database**: Robust data storage for article history and dynamic keywords, replacing fragile JSON files.
- **Deduplication**: Remembers sent articles to avoid duplicates.
- **Startup Fetch**: Immediately finds 4 fresh articles on restart.
- **Interactive**: "Remove ❌" button to delete unwanted messages.

## Setup

### 1. Prerequisites

- **Python 3.10+**
- **Ollama**: Download and install from [ollama.com](https://ollama.com).
  - Pull the default model: `ollama pull llama3.2` (or your preferred model).

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file with your keys:

```ini
TELEGRAM_BOT_TOKEN=your_token_here
CHANNEL_ID=-1001234567890
CHECK_INTERVAL_MINUTES=60
ADMIN_IDS=12345678,98765432
OLLAMA_MODEL=llama3.2
```

### 4. Run the Bot

```bash
python bot.py
```

_The bot will automatically initialize the SQLite database (`bot_data.db`) and migrate any old data on the first run._

## 🤖 Commands

| Command           | Usage                              | Description                                                   |
| :---------------- | :--------------------------------- | :------------------------------------------------------------ |
| `/ask`            | `/ask What is the latest on PDPA?` | **Ask a question** based on the news articles.                |
| `/status`         | `/status`                          | View bot uptime, source count, and DB stats.                  |
| `/force_fetch`    | `/force_fetch`                     | Trigger an immediate check for new articles.                  |
| `/add_keyword`    | `/add_keyword GenAI`               | Add a new tracking keyword instantly.                         |
| `/remove_keyword` | `/remove_keyword NFT`              | Remove a tracking keyword.                                    |
| `/list_keywords`  | `/list_keywords`                   | Show all active keywords.                                     |
| `/share`          | `/share <url>`                     | Manually scrape and share an article URL.                     |
| `/search`         | `/search <query>`                  | Search past articles by **Title**, **Category**, or **Tags**. |

## Code Architecture

- **`bot.py`**: Main entry point, Telegram handlers, and job queue.
- **`rag_engine.py`**: Manages **ChromaDB** (vector storage) and **Ollama** (generation) for the `/ask` command.
- **`scrapers.py`**: Contains custom logic to scrape sites like **PDPC** that don't provide RSS feeds.
- **`fetcher.py`**: Orchestrates fetching from both RSS feeds and custom scrapers.
- **`processor.py`**: Handles NLP tasks: keyword matching, categorization, and summarization.
- **`storage.py`**: SQLite database interface for storing article history and keywords.

## Troubleshooting

- **Ollama Error**: If `/ask` fails, ensure Ollama is running (`ollama serve`) and the model specified in `.env` matches what you pulled.
- **Database**: If you need to reset the data, delete `bot_data.db` and the bot will recreate it fresh on restart.
- **Migration**: Old `history.json` files are renamed to `.bak` after successful migration.
