import logging
import asyncio

from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, ContextTypes, CallbackQueryHandler, CommandHandler, Application, MessageHandler, filters
from telegram.error import TelegramError

from config import TELEGRAM_BOT_TOKEN, CHANNEL_ID, CHECK_INTERVAL_MINUTES, RSS_FEEDS, ADMIN_IDS, DEFAULT_KEYWORDS
from fetcher import RSSFetcher
from processor import ArticleProcessor
from storage import Storage
from rag_engine import RagEngine
import uuid

# Global Cache for /summarise -> Share flow
# Key: UUID, Value: Article Data Dict
TEMP_ARTICLE_CACHE = {}

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# Silence httpx logs (getUpdates polling)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Initialize components
fetcher = RSSFetcher(RSS_FEEDS)
processor = ArticleProcessor()
storage = Storage()
# Initialize RAG Engine (Global)
rag_engine = RagEngine()
START_TIME = datetime.now()

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
            # Store title, summary, category, and tags for search
            storage.add_article(
                url, 
                article_data['title'], 
                processed_data['summary'],
                processed_data.get('category'),
                processed_data['hashtags']
            )
            
            # Index manually shared article
            try:
                rag_engine.index_article(
                    text=f"{article_data['title']}\n\n{article_data['summary']}",
                    metadata={
                        'source': article_data['source'],
                        'title': article_data['title'],
                        'link': article_data['link'],
                        'published_str': str(article_data['published'])
                    }
                )
            except Exception as e:
                logger.error(f"Manual RAG Indexing failed: {e}")
                
            await update.message.reply_text("✅ Article shared successfully.")
            
        else:
            await update.message.reply_text("❌ Failed to process article.")
            
    except Exception as e:
        logger.error(f"Share command failed: {e}")
        await update.message.reply_text(f"❌ Error sharing article: {e}")

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Searches for past articles. Usage: /search <query>"""
    # Allow all users to search? Or just admins? 
    # User request implied utility for subscribers, but let's stick to admins for now unless specified otherwise,
    # actually request said "Users can search", so let's allow everyone.
    
    if not context.args:
        await update.message.reply_text("Usage: /search <topic>")
        return

    query = " ".join(context.args)
    results = storage.search_articles(query)
    
    if not results:
        await update.message.reply_text(f"No articles found for '<b>{query}</b>'.", parse_mode='HTML')
        return
        
    msg = f"🔍 <b>Search Results for '{query}':</b>\n\n"
    for link, title, created_at, category, tags in results:
        # Fallback if title is None (legacy data)
        display_title = title if title else link
        # Truncate date
        date_str = created_at.split(' ')[0]
        
        # Format tags nicely
        tag_str = ""
        if category:
            tag_str += f"[{category}]"
        
        msg += f"• <a href='{link}'>{display_title}</a>\n  <i>{date_str} {tag_str}</i>\n"
        
    await update.message.reply_text(msg, parse_mode='HTML', disable_web_page_preview=True)

async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Answers questions using RAG. Usage: /ask <question>"""
    if not context.args:
        await update.message.reply_text("Usage: /ask <question>")
        return
    
    query = " ".join(context.args)
    await update.message.reply_text(f"🤔 Thinking about: '{query}'...")
    
    try:
        # Run in thread to avoid blocking main loop
        response = await asyncio.to_thread(rag_engine.generate_answer, query)
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ask command failed: {e}")
        await update.message.reply_text("❌ An error occurred while generating the answer.")

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles private messages. 
    If a URL is sent, summarizes it.
    """
    text = update.message.text
    if not text:
        return

    # simple regex for url
    import re
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    
    if not urls:
        # Ignore non-URL text in DMs to avoids being annoying? 
        # Or reply with help? Let's ignore for now.
        return

    # Process first URL found
    url = urls[0]
    await update.message.reply_text("🤔 Reading and summarizing...")
    
    try:
        from goose3 import Goose
        g = Goose()
        article = g.extract(url=url)
        
        if not article.title:
            await update.message.reply_text("❌ Could not extract article content.")
            g.close()
            return

        # Prepare for processor
        article_data = {
            "title": article.title,
            "link": url,
            "summary": article.cleaned_text[:2000], 
            "published": datetime.now(),
            "source": article.domain or "Private Share"
        }
        g.close()
        
        # We need keywords for hashtag generation, use current ones
        current_keywords = storage.get_keywords()
        processed_data = processor.process_article(article_data, current_keywords)
        
        if processed_data:
            import html
            safe_title = html.escape(article_data['title'])
            
            # Replying privately
            response = (
                f"<b>{safe_title}</b>\n\n"
                f"{processed_data['summary']}\n\n"
                f"{processed_data['hashtags']}"
            )
            
            # --- Related Articles Logic ---
            category = processed_data.get('category')
            if category:
                # Search for articles in the same category
                results = storage.search_articles(category)
                
                # Filter out the current article (check against link)
                # results is list of tuples: (link, title, created_at, category, tags)
                related = [r for r in results if r[0] != url][:3]
                
                if related:
                    response += "\n\n📚 <b>Related from History:</b>\n"
                    for link, title, created_at, _, _ in related:
                        # Fallback title
                        display_title = title if title else link
                        response += f"• <a href='{link}'>{display_title}</a>\n"

            await update.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)
            # NOTE: We do NOT add to storage here. This is a private utility.
            
        else:
            await update.message.reply_text("❌ Failed to generate summary.")

    except Exception as e:
        logger.error(f"Private summary failed: {e}")
        await update.message.reply_text("❌ Error processing link.")

async def summarise_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Summarises a URL and offers to share it.
    Usage: /summarise <url>
    """
    if not context.args:
        await update.message.reply_text("Usage: /summarise <url>")
        return

    url = context.args[0]
    await update.message.reply_text("🤔 Reading and summarizing...")

    try:
        from goose3 import Goose
        g = Goose()
        article = g.extract(url=url)
        
        if not article.title:
            await update.message.reply_text("❌ Could not extract article content.")
            g.close()
            return

        # Prepare for processor
        article_data = {
            "title": article.title,
            "link": url,
            "summary": article.cleaned_text[:2000], 
            "published": datetime.now(),
            "source": article.domain or "Manual Summary"
        }
        g.close()
        
        # Process
        current_keywords = storage.get_keywords()
        processed_data = processor.process_article(article_data, current_keywords)
        
        if processed_data:
            import html
            safe_title = html.escape(article_data['title'])
            
            # Form response
            response = (
                f"<b>{safe_title}</b>\n\n"
                f"{processed_data['summary']}\n\n"
                f"{processed_data['hashtags']}"
            )
            
            # Store in Cache for Sharing
            cache_id = str(uuid.uuid4())
            TEMP_ARTICLE_CACHE[cache_id] = {
                'article': article_data,
                'processed': processed_data
            }
            
            # Add Share Button
            keyboard = [[InlineKeyboardButton("Share to Channel 📢", callback_data=f"share|{cache_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(response, parse_mode='HTML', reply_markup=reply_markup)
            
        else:
            await update.message.reply_text("❌ Failed to generate summary.")

    except Exception as e:
        logger.error(f"Summarise command failed: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

# --- Existing Handlers ---

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles callback queries (Remove message, Share article)."""
    query = update.callback_query
    await query.answer() # Acknowledge
    
    data = query.data
    
    # --- Remove Action ---
    if data == "remove":
        try:
            await query.delete_message()
            logger.info("Message removed by user.")
        except TelegramError as e:
            logger.error(f"Failed to delete message: {e}")
            
    # --- Share Action ---
    elif data.startswith("share|"):
        _, cache_id = data.split("|")
        cached_item = TEMP_ARTICLE_CACHE.get(cache_id)
        
        if not cached_item:
            await query.edit_message_text(text="❌ Error: Article data expired or not found.")
            return
            
        article_data = cached_item['article']
        processed_data = cached_item['processed']
        
        # Construct Channel Message
        import html
        safe_title = html.escape(article_data['title'])
        category_tag = f"<b>[{processed_data.get('category', 'Tech Law')}]</b>"
        manual_tag = "\n<i>(Shared via /summarise)</i>"
        
        message = f"{category_tag}\n" \
                  f"<b>{safe_title}</b>\n\n" \
                  f"{processed_data['summary']}\n\n" \
                  f"Source: {article_data['source']}\n" \
                  f"{processed_data['hashtags']}\n" \
                  f"{manual_tag}\n\n" \
                  f"<a href='{article_data['link']}'>Read Full Article</a>"
        
        # Add Remove Button for the channel message
        keyboard = [[InlineKeyboardButton("Remove ❌", callback_data="remove")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            # Send to Channel
            await context.bot.send_message(
                chat_id=CHANNEL_ID, 
                text=message, 
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
            # Store & Index
            try:
                storage.add_article(
                    article_data['link'], 
                    article_data['title'], 
                    processed_data['summary'],
                    processed_data.get('category'),
                    processed_data['hashtags']
                )
                
                rag_engine.index_article(
                    text=f"{article_data['title']}\n\n{article_data['summary']}",
                    metadata={
                        'source': article_data['source'],
                        'title': article_data['title'],
                        'link': article_data['link'],
                        'published_str': str(article_data['published'])
                    }
                )
            except Exception as e:
                logger.error(f"Storage/Indexing failed during share: {e}")

            # Update the button text to show success on the user's side
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(f"✅ Shared <b>{safe_title}</b> to channel!", parse_mode='HTML')
            
            # Clear cache
            del TEMP_ARTICLE_CACHE[cache_id]
            
        except Exception as e:
            logger.error(f"Failed to share article: {e}")
            await query.message.reply_text("❌ Failed to share article to channel.")

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
                    
                    # Mark as sent - STORE METADATA NOW
                    storage.add_article(
                        link, 
                        article['title'], 
                        processed_data['summary'],
                        processed_data.get('category'),
                        processed_data['hashtags']
                    )
                    count += 1
                    
                    await asyncio.sleep(2) 
                    
                    # RAG Indexing
                    try:
                        # Index relevant article
                        rag_engine.index_article(
                            text=f"{article['title']}\n\n{article['summary']}",
                            metadata={
                                'source': article['source'],
                                'title': article['title'],
                                'link': article['link'],
                                'published_str': str(article['published'])
                            }
                        )
                    except Exception as e:
                        logger.error(f"RAG Indexing failed: {e}")
                    
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
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("ask", ask_command))
    application.add_handler(CommandHandler("summarise", summarise_command))
    application.add_handler(CommandHandler("summarize", summarise_command))
    
    # Private Message Handler (for Summarizer)
    # Filters: Text AND Private Chat AND Not a Command
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, 
        handle_private_message
    ))
    
    # Add Callback Handler - Handles "remove" (channel) AND "share|..." (summarise)
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Add Error Handler
    application.add_error_handler(error_handler)

    # Job Queue
    job_queue = application.job_queue
    
    # Run startup job after 5 seconds
    job_queue.run_once(startup_job, 5)
    
    # Run periodic job
    job_queue.run_repeating(scheduled_job, interval=CHECK_INTERVAL_MINUTES * 60, first=60)

    logger.info(f"Bot started. Checking every {CHECK_INTERVAL_MINUTES} minutes.")
    application.run_polling()
