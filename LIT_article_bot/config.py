import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Check if keys are present
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables.")
if not GOOGLE_API_KEY:
    raise ValueError("No GOOGLE_API_KEY found in environment variables.")

# Bot Configuration
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))
CHANNEL_ID = os.getenv("CHANNEL_ID") # Can be a channel username like @channelname or an integer ID

# Filtering
KEYWORDS = [
    "AI", "Artificial Intelligence", 
    "Copyright", "IP", "Intellectual Property", 
    "Regulation", "Data Privacy", "GDPR",
    "Machine Learning", "Deepfakes", 
    "Generative AI", "LLM", 
    "Tech Policy", "Antitrust", "Cybersecurity",
    "Emerging Tech", "Quantum Computing", "Blockchain Law"
]

# Data Sources (RSS Feeds)
RSS_FEEDS = [
    # "https://cyber.harvard.edu/feed",  # Harvard Berkman Klein Center (Parsing error)
    "https://hai.stanford.edu/news/feed", # Stanford HAI (Check if this feed is valid, otherwise usually they have one)
    "https://www.eff.org/rss/updates.xml", # EFF
    "https://www.lawfareblog.com/feeds/feed", # Lawfare
    "https://feeds.feedburner.com/TechCrunch", # TechCrunch (Needs heavy filtering)
    "https://www.theverge.com/rss/policy/index.xml", # The Verge Policy
    "https://arxiv.org/rss/cs.CY", # ArXiv Computers and Society (Very academic, good for emerging tech)
]
