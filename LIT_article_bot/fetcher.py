import feedparser
import logging
import requests
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import time

logger = logging.getLogger(__name__)

class RSSFetcher:
    def __init__(self, sources):
        self.sources = sources
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, application/atom+xml, text/xml, */*'
        }
    
    def fetch_updates(self, last_check_time=None):
        """
        Fetches articles from RSS feeds.
        If last_check_time is provided, only returns articles published after that time.
        """
        articles = []
        
        for source in self.sources:
            try:
                # Use requests to fetch the feed content
                response = requests.get(source, headers=self.headers, timeout=15)
                response.raise_for_status()
                
                # Parse the content
                feed = feedparser.parse(response.content)
                
                # Log feed title for debugging
                logger.debug(f"Fetched feed: {feed.feed.get('title', 'Unknown Title')}")

                # Even if bozo is True, feedparser might have recovered some data.
                # We only skip if there are no entries.
                if not feed.entries:
                    if feed.bozo:
                        logger.warning(f"Error parsing feed {source}: {feed.bozo_exception}")
                    else:
                        logger.warning(f"No entries found for {source}")
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
            except requests.RequestException as e:
                logger.error(f"Network error fetching {source}: {e}")
            except Exception as e:
                logger.error(f"Error processing {source}: {e}")
                
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
