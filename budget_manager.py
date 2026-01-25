
import json
import os
from datetime import datetime
from utils import log

BUDGET_FILE = "budget_tracker.json"

# Limits based on $50/mo plan
LIMITS = {
    "tweets_sent": 600,       # $6.00
    "interactions": 1000,     # $15.00
    "tweets_read": 6000,      # $30.00
    "users_read": 500         # $5.00
}

class BudgetManager:
    def __init__(self):
        self.usage = self._load_usage()

    def _load_usage(self):
        # Reset if new month
        current_month = datetime.now().strftime("%Y-%m")
        
        default = {
            "month": current_month,
            "tweets_sent": 0,
            "interactions": 0,
            "tweets_read": 0,
            "users_read": 0
        }

        if not os.path.exists(BUDGET_FILE):
            return default

        try:
            with open(BUDGET_FILE, 'r') as f:
                data = json.load(f)
                if data.get("month") != current_month:
                    log("BUDGET", "📅 New month detected. Resetting budget counters.")
                    return default
                return data
        except Exception:
            return default

    def _save_usage(self):
        with open(BUDGET_FILE, 'w') as f:
            json.dump(self.usage, f)

    def can_spend(self, category, amount=1):
        """
        Check if we have budget for X amount of category.
        categories: 'tweets_sent', 'interactions', 'tweets_read', 'users_read'
        """
        current = self.usage.get(category, 0)
        limit = LIMITS.get(category, 0)
        
        if current + amount > limit:
            log("BUDGET", f"⚠️ BUDGET EXCEEDED for {category}. ({current}/{limit}). Action blocked.")
            return False
        return True

    def record_spend(self, category, amount=1):
        """
        Record usage.
        """
        if category in self.usage:
            self.usage[category] += amount
            self._save_usage()
            # log("BUDGET", f"💸 Spend recorded: {category} +{amount} (Total: {self.usage[category]})")

# Singleton instance
budget = BudgetManager()
