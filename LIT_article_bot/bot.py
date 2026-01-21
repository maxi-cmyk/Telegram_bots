import logging
import asyncio
import time
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, ContextTypes, CallbackQueryHandler, CommandHandler, Application
from telegram.error import TelegramError

from config import TELEGRAM_BOT_TOKEN, CHANNEL_ID, CHECK_INTERVAL_MINUTES, RSS_FEEDS, ADMIN_IDS, DEFAULT_KEYWORDS

# ... (imports)

# --- Helper Checks ---
def is_admin(user_id):
    if 0 in ADMIN_IDS:
        logger.warning(f"Allowed admin command in DEV MODE (ADMIN_ID=0) for User ID: {user_id}")
        return True 
    
    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized admin attempt by User ID: {user_id}")
        return False
        
    return True

# --- Error Handler ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log the error and send a telegram message to notify the developer."""
    logger.error(f"Exception while handling an update: {context.error}")

    # Traceback
    import traceback
    import html
    
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    message = (
        f"🚨 <b>An exception occurred:</b>\n"
        f"<pre>{html.escape(str(context.error))}</pre>\n\n"
        f"<b>Traceback:</b>\n"
        f"<pre>{html.escape(tb_string[-1500:])}</pre>"
    )

    for admin_id in ADMIN_IDS:
        if admin_id != 0:
            try:
                await context.bot.send_message(chat_id=admin_id, text=message, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Failed to send error report to admin {admin_id}: {e}")


# --- Command Handlers ---

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reports bot health and statistics."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Access Denied: You are not the configured admin.")
        return

    uptime = datetime.now() - START_TIME
    msg = (
        f"✅ <b>Bot Status: Online</b>\n"
        f"⏱ Uptime: {str(uptime).split('.')[0]}\n"
        f"📡 Sources: {len(RSS_FEEDS)}\n"
        f"🔑 Active Keywords: {len(storage.get_keywords())}\n"
        f"📚 History Size: {storage.get_history_count()}\n"
        f"📅 Check Interval: {CHECK_INTERVAL_MINUTES} mins"
    )
    await update.message.reply_text(msg, parse_mode='HTML')

async def force_fetch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually triggers the fetch job."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Access Denied: You are not the configured admin.")
        return

    await update.message.reply_text("🔄 Force fetching articles...")
    logger.info("Manual force fetch triggered.")
    
    # Run the scheduled logic immediately
    # We pass 'context' but verify if scheduled_job uses it correctly (yes)
    await scheduled_job(context)
    
    await update.message.reply_text("Fetch complete.")

async def list_keywords_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all active keywords."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Access Denied: You are not the configured admin.")
        return

    keywords = storage.get_keywords()
    if not keywords:
        await update.message.reply_text("No keywords set.")
        return
        
    # Join
    msg = "<b> Active Keywords:</b>\n" + ", ".join(keywords)
    await update.message.reply_text(msg, parse_mode='HTML')

async def add_keyword_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adds a keyword. Usage: /add_keyword <word>"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Access Denied: You are not the configured admin.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /add_keyword <word>")
        return
    
    # Handle multi-word keywords properly if passed as one string? 
    # Telegram args splits by space. If user sends "/add_keyword machine learning", args=['machine', 'learning']
    keyword = " ".join(context.args)
    
    if storage.add_keyword(keyword):
        await update.message.reply_text(f"Added keyword: <b>{keyword}</b>", parse_mode='HTML')
        logger.info(f"Keyword added: {keyword}")
    else:
        await update.message.reply_text(f"Keyword <b>{keyword}</b> already exists.", parse_mode='HTML')

async def remove_keyword_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Removes a keyword. Usage: /remove_keyword <word>"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Access Denied: You are not the configured admin.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /remove_keyword <word>")
        return
    
    keyword = " ".join(context.args)
    
    if storage.remove_keyword(keyword):
        await update.message.reply_text(f"🗑 Removed keyword: <b>{keyword}</b>", parse_mode='HTML')
        logger.info(f"Keyword removed: {keyword}")
    else:
        await update.message.reply_text(f"Keyword <b>{keyword}</b> not found.", parse_mode='HTML')

async def share_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually shares an article. Usage: /share <url>"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Access Denied: You are not the configured admin.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /share <url>")
        return
    
    url = context.args[0]
    await update.message.reply_text("🔄 Scraping and processing article...")

    try:
        from goose3 import Goose
        g = Goose()
        article = g.extract(url=url)
        
        # Parse published date (fallback to now)
        published = datetime.now()
        
        # Construct article object compatible with processor
        article_data = {
            "title": article.title,
            "link": url,
            "summary": article.cleaned_text[:2000], # Use cleaned text for AI summary context
            "published": published,
            "source": article.domain or "Manual Share"
        }
        
        # Clean up resources
        g.close()
        
        # Process using existing logic
        current_keywords = storage.get_keywords()
        processed_data = processor.process_article(article_data, current_keywords)
        
        if processed_data:
            import html
            safe_title = html.escape(article_data['title'])
            
            category_tag = f"<b>[{processed_data.get('category', 'Tech Law')}]</b>"
            # Manually added tag
            manual_tag = "\n<i>(Manually Shared)</i>"
            
            message = f"{category_tag}\n" \
                      f"<b>{safe_title}</b>\n\n" \
                      f"{processed_data['summary']}\n\n" \
                      f"Source: {article_data['source']}\n" \
                      f"{processed_data['hashtags']}\n" \
                      f"{manual_tag}\n\n" \
                      f"<a href='{article_data['link']}'>Read Full Article</a>"
            
            # Add Remove Button
            keyboard = [[InlineKeyboardButton("Remove ❌", callback_data="remove")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=CHANNEL_ID, 
                text=message, 
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
            # Add to storage so we don't duplicate if it comes in via RSS later
            storage.add_article(url)
            await update.message.reply_text("✅ Article shared successfully.")
            
        else:
            await update.message.reply_text("❌ Failed to process article.")
            
    except Exception as e:
        logger.error(f"Share command failed: {e}")
        await update.message.reply_text(f"❌ Error sharing article: {e}")

# --- Existing Handlers ---

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
    
    # Get current dynamic keywords
    current_keywords = storage.get_keywords()

    for article in articles:
        if limit and count >= limit:
            break
            
        link = article['link']
        if not storage.is_new(link):
            continue

        if processor.is_relevant(article, current_keywords):
            logger.info(f"Processing relevant article: {article['title']}")
            
            processed_data = processor.process_article(article, current_keywords)
            
            if processed_data:
                # Escape title to prevent HTML errors
                import html
                safe_title = html.escape(article['title'])
                
                category_tag = f"<b>[{processed_data.get('category', 'Tech Law')}]</b>"
                message = f"{category_tag}\n" \
                          f"<b>{safe_title}</b>\n\n" \
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
    
    # Reload history from disk to ensure we have the latest state
    # storage.history = storage.load_history() # REMOVED: SQLite handles persistence
    logger.info(f"Loaded {storage.get_history_count()} articles from history.")
    
    # Check if keywords need initialization
    if not storage.get_keywords():
        logger.info("Initializing default keywords...")
        for k in DEFAULT_KEYWORDS:
            storage.add_keyword(k)
    
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

    # Add Command Handlers
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("force_fetch", force_fetch_command))
    application.add_handler(CommandHandler("add_keyword", add_keyword_command))
    application.add_handler(CommandHandler("remove_keyword", remove_keyword_command))
    application.add_handler(CommandHandler("list_keywords", list_keywords_command))
    application.add_handler(CommandHandler("share", share_command))
    
    # Add Callback Handler
    application.add_handler(CallbackQueryHandler(remove_article, pattern="^remove$"))

    # Add Error Handler
    application.add_error_handler(error_handler)

    # Job Queue
    job_queue = application.job_queue
    
    # Run startup job after 5 seconds
    job_queue.run_once(startup_job, 5)
    
    # Run periodic job
    # interval is in seconds
    job_queue.run_repeating(scheduled_job, interval=CHECK_INTERVAL_MINUTES * 60, first=60)

    logger.info(f"Bot started. Checking every {CHECK_INTERVAL_MINUTES} minutes.")
    application.run_polling()
