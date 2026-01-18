import json
import os
import logging

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self, filename="history.json"):
        self.filename = filename
        self.history = self.load_history()

    def load_history(self):
        """Loads the set of sent article links from JSON file."""
        if not os.path.exists(self.filename):
            return []
        try:
            with open(self.filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return []

    def save_history(self):
        """Saves the current history to JSON file."""
        try:
            with open(self.filename, 'w') as f:
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
