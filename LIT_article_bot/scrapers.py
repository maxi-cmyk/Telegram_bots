import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseScraper:
    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        }

    def fetch(self):
        try:
            response = requests.get(self.url, headers=self.headers, timeout=20)
            response.raise_for_status()
            return self.parse(response.content)
        except Exception as e:
            logger.error(f"Error scraping {self.name} ({self.url}): {e}")
            return []

    def parse(self, content):
        raise NotImplementedError("Subclasses must implement parse method")

class PDPCScraper(BaseScraper):
    def fetch(self):
        # PDPC uses an API: https://www.pdpc.gov.sg/api/pdpcpressroom/getpressroomlisting
        # Method: POST
        # Params: type=all&year=all&page=1
        
        target_url = "https://www.pdpc.gov.sg/api/pdpcpressroom/getpressroomlisting"
        payload = {
            "type": "all",
            "year": "all",
            "page": "1"
        }
        headers = self.headers.copy()
        headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        
        try:
            response = requests.post(target_url, data=payload, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()
            return self.parse(data)
        except Exception as e:
            logger.error(f"Error scraping PDPC API: {e}")
            return []

    def parse(self, data):
        articles = []
        # JSON structure: {'items': [{'title': '...', 'url': '...', 'date': '...'}, ...]}
        
        items = data.get('items', [])
        
        for item in items:
            title = item.get('title')
            rel_link = item.get('url')
            date_str = item.get('date') # Format usually "29 Jan 2024"
            
            if not title or not rel_link:
                continue
                
            link = rel_link
            if link.startswith('/'):
                link = "https://www.pdpc.gov.sg" + link
                
            published = datetime.now()
            if date_str:
                try:
                    # Date format example: "08 Oct 2024"
                    published = datetime.strptime(date_str, "%d %b %Y")
                except:
                    pass
            
            articles.append({
                "title": title,
                "link": link,
                "summary": item.get('description', ''), 
                "published": published,
                "source": "PDPC Singapore"
            })
            
        return articles


