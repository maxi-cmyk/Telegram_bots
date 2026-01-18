import google.generativeai as genai
import logging
from config import GOOGLE_API_KEY, KEYWORDS

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

class ArticleProcessor:
    def __init__(self):
        self.keywords = [k.lower() for k in KEYWORDS]

    def is_relevant(self, article):
        """
        Checks if the article is relevant based on keywords in title or summary.
        """
        text = (article['title'] + " " + article['summary']).lower()
        for keyword in self.keywords:
            if keyword in text:
                logger.info(f"Match found for keyword '{keyword}': {article['title']}")
                return True
        return False

    def process_article(self, article):
        """
        Summarizes the article and generates hashtags using Gemini.
        Returns a dictionary with summary and hashtags.
        """
        try:
            prompt = f"""
            You are a legal tech expert assistant.
            Please analyze the following article and:
            1. Classify it into ONE of these categories: [AI & Law, Quantum Computing, Cryptography, Renewable Energy/Sustainability, Intellectual Property, Data Privacy, Other].
            2. Summarize it in 2-3 concise sentences, focusing on the intersection of technology and law.
            3. Generate 2-3 relevant hashtags.
            
            Article Title: {article['title']}
            Article Content/Summary: {article['summary']}
            Article Link: {article['link']}

            Output format:
            Category: [Category Name]
            Summary: [Your summary here]
            Hashtags: [Hashtag1] [Hashtag2]
            """
            
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            # Simple parsing
            category = "General Tech Law"
            summary = ""
            hashtags = ""
            
            lines = text.split('\n')
            for line in lines:
                if line.startswith("Category:"):
                    category = line.replace("Category:", "").strip()
                elif line.startswith("Summary:"):
                    summary = line.replace("Summary:", "").strip()
                elif line.startswith("Hashtags:"):
                    hashtags = line.replace("Hashtags:", "").strip()
            
            # Fallback if parsing fails
            if not summary:
                summary = text 
            
            return {
                "category": category,
                "summary": summary,
                "hashtags": hashtags
            }
            
        except Exception as e:
            logger.error(f"Error processing article with Gemini: {e}")
            # Fallback to original summary
            return {
                "category": "Tech Law (Unclassified)",
                "summary": f"(AI Summary Unavailable) {article.get('summary', '')[:500]}...",
                "hashtags": "#TechLaw"
            }
