import logging
import re
from config import KEYWORDS

logger = logging.getLogger(__name__)

# Category Mapping
CATEGORY_MAP = {
    "AI & Law": ["AI", "Artificial Intelligence", "Machine Learning", "Generative AI", "LLM", "Deepfakes"],
    "Quantum Computing": ["Quantum"],
    "Cryptography": ["Cryptography", "Encryption", "Blockchain"],
    "Renewable Energy": ["Renewable Energy", "Green Tech", "Sustainability", "Climate Law"],
    "Intellectual Property": ["Copyright", "IP", "Intellectual Property"],
    "Data Privacy": ["Data Privacy", "GDPR", "Cybersecurity"],
    "Tech Policy": ["Regulation", "Tech Policy", "Antitrust", "Emerging Tech"]
}

class ArticleProcessor:
    def __init__(self):
        self.keywords = [k.lower() for k in KEYWORDS]

    def is_relevant(self, article):
        """
        Checks if the article is relevant based on keywords in title or summary.
        Uses regex word boundaries to avoid false positives.
        """
        text = (article['title'] + " " + article['summary']).lower()
        
        for keyword in self.keywords:
            pattern = re.compile(r'\b' + re.escape(keyword) + r'\b')
            if pattern.search(text):
                logger.info(f"Match found for keyword '{keyword}': {article['title']}")
                return True
        return False

    def process_article(self, article):
        """
        Processes article without AI.
        1. Uses original RSS summary.
        2. Heuristically determines Category.
        3. Generates Hashtags from keywords.
        """
        try:
            text = (article['title'] + " " + article['summary']).lower()
            
            # 1. Determine Category
            category = "General Tech Law"
            matched_keywords = []

            for cat, keywords in CATEGORY_MAP.items():
                for k in keywords:
                    if re.search(r'\b' + re.escape(k.lower()) + r'\b', text):
                        category = cat
                        break
            
            # 2. Generate Hashtags
            # Find all matching keywords for tags
            for k in self.keywords:
                if re.search(r'\b' + re.escape(k) + r'\b', text):
                    matched_keywords.append(k.replace(" ", ""))
            
            # Add category tag if unique
            cat_tag = category.replace(" ", "").replace("&", "")
            if cat_tag not in matched_keywords:
                matched_keywords.append(cat_tag)
                
            hashtags = " ".join([f"#{t}" for t in set(matched_keywords[:5])]) # Limit to 5 tags
            
            # 3. Clean Summary
            # We'll use the raw RSS summary but strip HTML tags and escape it for Telegram
            import html
            summary_text = article.get('summary', 'No summary available.')
            
            # Remove HTML tags (e.g. <div>, <p>, <a href...>)
            summary_text = re.sub(r'<[^>]+>', '', summary_text)
            
            # Escape valid HTML characters (<, >, &) so they don't break Telegram parsing
            summary_text = html.escape(summary_text)
            
            # Truncate if too long
            if len(summary_text) > 800:
                summary_text = summary_text[:800] + "..."

            return {
                "category": category,
                "summary": summary_text,
                "hashtags": hashtags
            }
            
        except Exception as e:
            logger.error(f"Error processing article: {e}")
            return None
