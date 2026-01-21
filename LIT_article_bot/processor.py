import logging
import re

logger = logging.getLogger(__name__)

# Category Mapping
# Note: New dynamic keywords won't automatically have a category unless added here.
# They will fall back to "General Tech Law".
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
        pass

    def is_relevant(self, article, keywords):
        """
        Checks if the article is relevant based on dynamic keywords.
        """
        text = (article['title'] + " " + article['summary']).lower()
        
        # keywords argument is expected to be a list of strings
        for keyword in keywords:
            pattern = re.compile(r'\b' + re.escape(keyword.lower()) + r'\b')
            if pattern.search(text):
                logger.info(f"Match found for keyword '{keyword}': {article['title']}")
                return True
        return False

    def process_article(self, article, keywords):
        """
        Processes article using dynamic keywords for hashtag generation.
        """
        try:
            text = (article['title'] + " " + article['summary']).lower()
            
            # 1. Determine Category
            category = "General Tech Law"
            matched_keywords = []

            for cat, cat_keys in CATEGORY_MAP.items():
                for k in cat_keys:
                    if re.search(r'\b' + re.escape(k.lower()) + r'\b', text):
                        category = cat
                        break
            
            # 2. Generate Hashtags
            # Find all matching keywords from the dynamic list
            for k in keywords:
                if re.search(r'\b' + re.escape(k.lower()) + r'\b', text):
                    matched_keywords.append(k.replace(" ", ""))
            
            # Add category tag if unique
            cat_tag = category.replace(" ", "").replace("&", "")
            if cat_tag not in matched_keywords:
                matched_keywords.append(cat_tag)
                
            hashtags = " ".join([f"#{t}" for t in set(matched_keywords[:5])]) # Limit to 5 tags
            
            # 3. Clean & Summarize
            import html
            import ollama
            from config import OLLAMA_MODEL

            # Basic clean of original summary for fallback
            original_summary = article.get('summary', 'No summary available.')
            original_summary = re.sub(r'<[^>]+>', '', original_summary)
            original_summary = html.escape(original_summary)

            summary_text = original_summary

            try:
                # Attempt AI Summarization
                prompt = (
                    f"Summarize the following tech/law article in 1-2 concise, high-impact sentences. "
                    f"Focus on the legal or technical implication. Do not use 'Here is a summary'. "
                    f"Title: {article['title']}\n"
                    f"Content: {original_summary}"
                )
                
                logger.info(f"Generating AI summary for: {article['title']}")
                response = ollama.chat(model=OLLAMA_MODEL, messages=[
                    {'role': 'user', 'content': prompt},
                ])
                
                ai_summary = response['message']['content'].strip()
                if ai_summary:
                    summary_text = f"✨ <b>AI Summary:</b> {html.escape(ai_summary)}"
                
            except Exception as e:
                logger.warning(f"Ollama summarization failed (using fallback): {e}")
                # Fallback is already set to original_summary
            
            # Truncate if too long (backup safety)
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
