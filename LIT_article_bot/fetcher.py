import feedparser
import logging
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import time

logger = logging.getLogger(__name__)

class RSSFetcher:
    def __init__(self, sources):
        self.sources = sources
    
    def fetch_updates(self, last_check_time=None):
        """
        Fetches articles from RSS feeds.
        If last_check_time is provided, only returns articles published after that time.
        """
        articles = []
        
        for source in self.sources:
            try:
                # Add User-Agent to avoid being blocked
                feed = feedparser.parse(source, agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                
                if feed.bozo:
                    logger.warning(f"Error parsing feed {source}: {feed.bozo_exception}")
                    continue
                
                for entry in feed.entries:
                    published_time = self._get_published_time(entry)
                    
                    if not published_time:
                        continue

                    # Filter by time if provided
                    if last_check_time and published_time <= last_check_time:
                        continue
                        
                    articles.append({
                        "title": entry.get("title", "No Title"),
                        "link": entry.get("link", ""),
                        "summary": entry.get("summary", "") or entry.get("description", ""),
                        "published": published_time,
                        "source": feed.feed.get("title", source)
                    })
            except Exception as e:
                logger.error(f"Error fetching {source}: {e}")
                
        # Sort by published time (newest first)
        articles.sort(key=lambda x: x['published'], reverse=True)
        return articles

    def _get_published_time(self, entry):
        # standard RSS published
        if 'published_parsed' in entry and entry.published_parsed:
            return datetime.fromtimestamp(time.mktime(entry.published_parsed))
        elif 'updated_parsed' in entry and entry.updated_parsed:
            return datetime.fromtimestamp(time.mktime(entry.updated_parsed))
        return None
