import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# AI Configuration
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
# RAG Configuration
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "chroma_db")


# Check if keys are present
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables.")


# Bot Configuration
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "30"))
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Admin Management (Supports multiple IDs comma-separated)
ADMIN_IDS = []
_admin_env = os.getenv("ADMIN_IDS", os.getenv("ADMIN_ID", "0"))
if _admin_env:
    try:
        ADMIN_IDS = [int(x.strip()) for x in _admin_env.split(",")]
    except ValueError:
        print("Warning: ADMIN_IDS contains non-numeric values.")


# Filtering
# KEYWORDS moved to keywords.json for dynamic management
# Default list preserved in case keywords.json is missing or corrupted
DEFAULT_KEYWORDS = [
    "AI", "Artificial Intelligence", 
    "Copyright", "IP", "Intellectual Property", 
    "Regulation", "Data Privacy", "GDPR",
    "Machine Learning", "Deepfakes", 
    "Generative AI", "LLM", 
    "Tech Policy", "Antitrust", "Cybersecurity",
    "Emerging Tech", "Quantum Computing", "Blockchain Law",
    "Cryptography", "Encryption", 
    "Renewable Energy", "Green Tech", "Sustainability", "Climate Law"
]

# Data Sources (RSS Feeds)
RSS_FEEDS = [
    # Global Tech & Law Policy
    "https://www.eff.org/rss/updates.xml", # EFF
    "https://www.theverge.com/rss/policy/index.xml", # The Verge Policy
    "https://artificiallawyer.com/feed/", # Artificial Lawyer
    "https://www.abajournal.com/rss/feeds/topics_Technology", # ABA Journal Tech
    "https://blog.ericgoldman.org/feed", # Eric Goldman (Tech & Marketing Law)
    "https://www.technologyreview.com/feed/", # MIT Technology Review
    "https://btlj.org/feed/", # Berkeley Technology Law Journal
    
    
    # Singapore Sources
    "https://www.businesstimes.com.sg/rss/technology", # Business Times Tech
    "https://thetechrevolutionist.com/category/tech-explained/feed", # The Tech Revolutionist (Tech Explained)
    "https://www.techgoondu.com/feed/", # TechGoondu
    "https://techforgoodinstitute.org/feed/", # Tech for Good Institute
    
    # Legal & Research
    "https://papers.ssrn.com/sol3/JELJOUR_RSS.cfm?journal_id=225", # SSRN Cyberspace Law
    "https://sso.agc.gov.sg/rss/new-legislation", # Singapore Statutes Online (New Legislation)
]

# Custom Scraper Sources (Name -> URL)
SCRAPER_SOURCES = {
    "PDPC": "https://www.pdpc.gov.sg/news-and-events/press-room", 
    # "MAS": "https://www.mas.gov.sg/news/media-releases", # Example, usually strict anti-bot
}
