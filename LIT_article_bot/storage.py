import sqlite3
import json
import os
import logging
import re
from datetime import datetime
from processor import CATEGORY_MAP

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self, db_file="bot_data.db"):
        self.db_file = db_file
        self.conn = self._get_connection()
        self._init_db()
        self._run_migration()
        self._backfill_metadata()

    def _get_connection(self):
        return sqlite3.connect(self.db_file, check_same_thread=False)

    def _init_db(self):
        """Creates tables if they don't exist and handles schema updates."""
        try:
            with self.conn:
                # History Table
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS history (
                        link TEXT PRIMARY KEY,
                        title TEXT,
                        summary TEXT,
                        category TEXT,
                        tags TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Keywords Table
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS keywords (
                        keyword TEXT PRIMARY KEY,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            
            # --- Schema Migration: Check for missing columns ---
            cursor = self.conn.execute("PRAGMA table_info(history)")
            columns = [info[1] for info in cursor.fetchall()]
            
            for col in ["title", "summary", "category", "tags"]:
                if col not in columns:
                    logger.info(f"Migrating DB: Adding '{col}' column to history...")
                    with self.conn:
                        self.conn.execute(f"ALTER TABLE history ADD COLUMN {col} TEXT")

        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")

    def _run_migration(self):
        """Migrates data from legacy JSON files if they exist."""
        # 1. Migrate History
        if os.path.exists("history.json"):
            logger.info("Migrating history.json to SQLite...")
            try:
                with open("history.json", 'r') as f:
                    history_data = json.load(f)
                
                # Legacy only had links
                with self.conn:
                    self.conn.executemany(
                        "INSERT OR IGNORE INTO history (link) VALUES (?)",
                        [(link,) for link in history_data]
                    )
                
                os.rename("history.json", "history.json.bak")
                logger.info("History migration complete. Renamed to history.json.bak")
            except Exception as e:
                logger.error(f"History migration failed: {e}")

        # 2. Migrate Keywords
        if os.path.exists("keywords.json"):
            logger.info("Migrating keywords.json to SQLite...")
            try:
                with open("keywords.json", 'r') as f:
                    keyword_data = json.load(f)
                    
                with self.conn:
                    self.conn.executemany(
                        "INSERT OR IGNORE INTO keywords (keyword) VALUES (?)",
                        [(k,) for k in keyword_data]
                    )
                
                os.rename("keywords.json", "keywords.json.bak")
                logger.info("Keywords migration complete. Renamed to keywords.json.bak")
            except Exception as e:
                logger.error(f"Keywords migration failed: {e}")

    def _backfill_metadata(self):
        """Attempts to generate category/tags for legacy articles from their URLs."""
        try:
            # Find articles with missing metadata
            cursor = self.conn.execute(
                "SELECT link FROM history WHERE category IS NULL OR tags IS NULL"
            )
            rows = cursor.fetchall()
            
            if not rows:
                return

            logger.info(f"Backfilling metadata for {len(rows)} articles...")
            
            keywords = self.get_keywords()
            # Compile keywords for speed
            kw_patterns = [(k, re.compile(r'\b' + re.escape(k.lower()) + r'\b')) for k in keywords]
            
            updates = []
            
            for (link,) in rows:
                text = link.lower()
                tags = []
                category = "General Tech Law" # Default
                
                # 1. Determine Category from Map
                for cat, cat_keys in CATEGORY_MAP.items():
                    for k in cat_keys:
                        if k.lower() in text: # Simple text check for URL
                            category = cat
                            break
                    if category != "General Tech Law":
                        break
                
                # 2. Generate Tags from Keywords
                for k, pattern in kw_patterns:
                    # For URL, regex boundary might fail on hyphens. Simple check is safer for URLs.
                    if k.lower() in text: 
                        tags.append(f"#{k.replace(' ', '')}")
                
                # Add category tag if unique
                cat_tag = f"#{category.replace(' ', '').replace('&', '')}"
                if cat_tag not in tags:
                    tags.append(cat_tag)
                
                tags_str = " ".join(tags)
                updates.append((category, tags_str, link))
            
            with self.conn:
                self.conn.executemany(
                    "UPDATE history SET category = ?, tags = ? WHERE link = ?",
                    updates
                )
            logger.info("Metadata backfill complete.")
            
        except Exception as e:
            logger.error(f"Backfill failed: {e}")

    # --- History Management ---

    def is_new(self, link):
        """Checks if a link is new."""
        cursor = self.conn.execute("SELECT 1 FROM history WHERE link = ?", (link,))
        return cursor.fetchone() is None

    def add_article(self, link, title=None, summary=None, category=None, tags=None):
        """Adds a link to history with optional metadata."""
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT OR IGNORE INTO history (link, title, summary, category, tags) VALUES (?, ?, ?, ?, ?)", 
                    (link, title, summary, category, tags)
                )
        except sqlite3.Error as e:
            logger.error(f"Error adding article: {e}")

    def search_articles(self, query):
        """Search history for articles matching query (in title, summary, tags, or category)."""
        try:
            # Simple LIKE search
            search_query = f"%{query}%"
            cursor = self.conn.execute(
                """
                SELECT link, title, created_at, category, tags
                FROM history 
                WHERE title LIKE ? 
                   OR summary LIKE ? 
                   OR link LIKE ?
                   OR category LIKE ?
                   OR tags LIKE ?
                ORDER BY created_at DESC 
                LIMIT 10
                """, 
                (search_query, search_query, search_query, search_query, search_query)
            )
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Search error: {e}")
            return []

    def get_history_count(self):
        """Returns the number of articles in history."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM history")
        return cursor.fetchone()[0]

    # --- Keyword Management ---

    def get_keywords(self):
        """Returns list of active keywords."""
        try:
            cursor = self.conn.execute("SELECT keyword FROM keywords")
            return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error fetching keywords: {e}")
            return []

    def add_keyword(self, keyword):
        """Adds a keyword."""
        try:
            with self.conn:
                self.conn.execute("INSERT INTO keywords (keyword) VALUES (?)", (keyword,))
            return True
        except sqlite3.IntegrityError:
            return False # Already exists
        except sqlite3.Error as e:
            logger.error(f"Error adding keyword: {e}")
            return False

    def remove_keyword(self, keyword):
        """Removes a keyword."""
        try:
            with self.conn:
                cursor = self.conn.execute("DELETE FROM keywords WHERE keyword = ?", (keyword,))
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error removing keyword: {e}")
            return False

    def close(self):
        self.conn.close()
