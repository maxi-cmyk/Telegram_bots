import logging
import time
import schedule
import asyncio
from telegram import Bot
from telegram.error import TelegramError
from datetime import datetime, timedelta

from config import TELEGRAM_BOT_TOKEN, CHANNEL_ID, CHECK_INTERVAL_MINUTES, RSS_FEEDS
from fetcher import RSSFetcher
from processor import ArticleProcessor

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize components
fetcher = RSSFetcher(RSS_FEEDS)
processor = ArticleProcessor()
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# State to track last sent article time to avoid duplicates
# In a real prod app, use a database. For now, we use a simple timestamp.
last_check_time = datetime.now() - timedelta(hours=24) # Look back 24h on start

async def job():
    global last_check_time
    logger.info("Starting job: Fetching articles...")
    
    current_time = datetime.now()
    articles = fetcher.fetch_updates(last_check_time)
    
    if not articles:
        logger.info("No new articles found.")
    
    for article in articles:
        if processor.is_relevant(article):
            logger.info(f"Processing relevant article: {article['title']}")
            
            processed_data = processor.process_article(article)
            
            if processed_data:
                message = f"<b>{article['title']}</b>\n\n" \
                          f"{processed_data['summary']}\n\n" \
                          f"Source: {article['source']}\n" \
                          f"{processed_data['hashtags']}\n\n" \
                          f"<a href='{article['link']}'>Read Full Article</a>"
                
                try:
                    logger.info(f"Sending message for: {article['title']}")
                    await bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode='HTML')
                    # Rate limit slightly to avoid spamming Telegram API
                    time.sleep(2) 
                except TelegramError as e:
                    logger.error(f"Failed to send message: {e}")
            else:
                logger.warning(f"Failed to process article: {article['title']}")
        else:
            logger.info(f"Skipping irrelevant article: {article['title']}")

    # Update last check time
    last_check_time = current_time
    logger.info("Job finished.")

def run_schedule():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Run immediately on start
    loop.run_until_complete(job())
    
    # Schedule
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(lambda: loop.run_until_complete(job()))
    
    logger.info(f"Bot started. Checking every {CHECK_INTERVAL_MINUTES} minutes.")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    run_schedule()
