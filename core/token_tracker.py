from core.config_manager import ConfigManager

class TokenTracker:
    """
    Handles token usage estimation and persistence for transparency.
    """
    
    def __init__(self, config: ConfigManager):
        self.config = config

    def track_usage(self, text_input: str, text_output: str) -> int:
        """
        Estimates token count for the exchange and updates persistent storage.
        Heuristic: Character Count / 4.
        """
        total_chars = len(text_input) + len(text_output)
        tokens = max(1, total_chars // 4)
        
        current_total = self.config.get("total_tokens_used", 0)
        self.config.set("total_tokens_used", current_total + tokens)
        
        return tokens

    def get_remaining_credits(self, limit: int = 1000000) -> float:
        """
        Returns the percentage of credits used (0.0 to 1.0).
        """
        used = self.config.get("total_tokens_used", 0)
        return min(1.0, used / limit)

    def get_usage_summary(self) -> str:
        """
        Returns a human-readable usage summary.
        """
        used = self.config.get("total_tokens_used", 0)
        return f"{used:,} tokens used"
