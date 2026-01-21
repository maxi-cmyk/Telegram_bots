import sqlite3
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self, db_file="bot_data.db"):
        self.db_file = db_file
        self.conn = self._get_connection()
        self._init_db()
        self._run_migration()

    def _get_connection(self):
        return sqlite3.connect(self.db_file, check_same_thread=False)

    def _init_db(self):
        """Creates tables if they don't exist."""
        try:
            with self.conn:
                # History Table
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS history (
                        link TEXT PRIMARY KEY,
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

    # --- History Management ---

    def is_new(self, link):
        """Checks if a link is new."""
        cursor = self.conn.execute("SELECT 1 FROM history WHERE link = ?", (link,))
        return cursor.fetchone() is None

    def add_article(self, link):
        """Adds a link to history."""
        try:
            with self.conn:
                self.conn.execute("INSERT OR IGNORE INTO history (link) VALUES (?)", (link,))
        except sqlite3.Error as e:
            logger.error(f"Error adding article: {e}")

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
