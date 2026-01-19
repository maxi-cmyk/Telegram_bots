import json
import os
import logging

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self, history_file="history.json", keywords_file="keywords.json"):
        self.history_file = history_file
        self.keywords_file = keywords_file
        self.history = self.load_history()
        self.keywords = self.load_keywords()

    def load_history(self):
        """Loads the set of sent article links from JSON file."""
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return []

    def save_history(self):
        """Saves the current history to JSON file."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f)
        except Exception as e:
            logger.error(f"Error saving history: {e}")

    def is_new(self, link):
        """Checks if a link is new (not in history)."""
        return link not in self.history

    def add_article(self, link):
        """Adds a link to history and saves."""
        if link not in self.history:
            self.history.append(link)
            # Optional: Limit history size to prevent file growing indefinitely
            if len(self.history) > 1000:
                 self.history = self.history[-1000:]
            self.save_history()

    # --- Keyword Management ---

    def load_keywords(self):
        """Loads keywords from JSON file."""
        if not os.path.exists(self.keywords_file):
            return []
        try:
            with open(self.keywords_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading keywords: {e}")
            return []

    def save_keywords(self):
        """Saves keywords to JSON file."""
        try:
            with open(self.keywords_file, 'w') as f:
                json.dump(self.keywords, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving keywords: {e}")

    def get_keywords(self):
        return self.keywords

    def add_keyword(self, keyword):
        if keyword not in self.keywords:
            self.keywords.append(keyword)
            self.save_keywords()
            return True
        return False

    def remove_keyword(self, keyword):
        if keyword in self.keywords:
            self.keywords.remove(keyword)
            self.save_keywords()
            return True
        return False
