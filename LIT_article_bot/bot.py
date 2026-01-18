import logging
import asyncio
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, ContextTypes, CallbackQueryHandler, Application
from telegram.error import TelegramError

from config import TELEGRAM_BOT_TOKEN, CHANNEL_ID, CHECK_INTERVAL_MINUTES, RSS_FEEDS
from fetcher import RSSFetcher
from processor import ArticleProcessor
from storage import Storage

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize components
fetcher = RSSFetcher(RSS_FEEDS)
processor = ArticleProcessor()
storage = Storage()

async def remove_article(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback query handler to remove a message."""
    query = update.callback_query
    await query.answer() # Acknowledge the callback
    try:
        await query.delete_message()
        logger.info("Message removed by user.")
    except TelegramError as e:
        logger.error(f"Failed to delete message: {e}")

async def process_and_send(context: ContextTypes.DEFAULT_TYPE, articles, limit=None):
    """Processes fetched articles and sends them."""
    count = 0
    
    # Sort articles by date (newest first)
    articles.sort(key=lambda x: x['published'], reverse=True)

    for article in articles:
        if limit and count >= limit:
            break
            
        link = article['link']
        if not storage.is_new(link):
            continue

        if processor.is_relevant(article):
            logger.info(f"Processing relevant article: {article['title']}")
            
            processed_data = processor.process_article(article)
            
            if processed_data:
                message = f"<b>{article['title']}</b>\n\n" \
                          f"{processed_data['summary']}\n\n" \
                          f"Source: {article['source']}\n" \
                          f"{processed_data['hashtags']}\n\n" \
                          f"<a href='{article['link']}'>Read Full Article</a>"
                
                # Add Remove Button
                keyboard = [
                    [InlineKeyboardButton("Remove ❌", callback_data="remove")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                try:
                    logger.info(f"Sending message for: {article['title']}")
                    await context.bot.send_message(
                        chat_id=CHANNEL_ID, 
                        text=message, 
                        parse_mode='HTML',
                        reply_markup=reply_markup
                    )
                    
                    # Mark as sent
                    storage.add_article(link)
                    count += 1
                    
                    # Rate limit
                    await asyncio.sleep(2) 
                    
                except TelegramError as e:
                    logger.error(f"Failed to send message: {e}")
            else:
                logger.warning(f"Failed to process article: {article['title']}")
        else:
            # Optionally mark irrelevant articles as seen so we don't check them again? 
            # For now, we only store SENT articles to keep history clean.
            pass

async def scheduled_job(context: ContextTypes.DEFAULT_TYPE):
    """Periodic job to check for updates."""
    logger.info("Starting scheduled job...")
    
    # Look back since last interval (plus a buffer)
    lookback = datetime.now() - timedelta(minutes=CHECK_INTERVAL_MINUTES + 30)
    articles = fetcher.fetch_updates(lookback)
    
    if not articles:
        logger.info("No new articles found.")
        return

    await process_and_send(context, articles)
    logger.info("Scheduled job finished.")

async def startup_job(context: ContextTypes.DEFAULT_TYPE):
    """Job to run on startup: fetch 4 unique articles from last 7 days."""
    logger.info("Running startup job...")
    
    lookback = datetime.now() - timedelta(days=7)
    articles = fetcher.fetch_updates(lookback)
    
    if not articles:
        logger.info("No articles found for startup.")
        return

    # We want 4 unique articles
    # process_and_send handles filtering and limiting
    await process_and_send(context, articles, limit=4)
    logger.info("Startup job finished.")


if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is missing!")
        exit(1)

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Add Handlers
    application.add_handler(CallbackQueryHandler(remove_article, pattern="^remove$"))

    # Job Queue
    job_queue = application.job_queue
    
    # Run startup job after 5 seconds
    job_queue.run_once(startup_job, 5)
    
    # Run periodic job
    # interval is in seconds
    job_queue.run_repeating(scheduled_job, interval=CHECK_INTERVAL_MINUTES * 60, first=60)

    logger.info(f"Bot started. Checking every {CHECK_INTERVAL_MINUTES} minutes.")
    application.run_polling()
