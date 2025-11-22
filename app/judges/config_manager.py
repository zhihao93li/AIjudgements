import json
import os
from typing import Dict, Any
from loguru import logger
from app.judges.prompts import DEFAULT_JUDGE_PERSONAS

CONFIG_FILE = "judge_config.json"

class JudgeConfigManager:
    def __init__(self):
        self.config_path = os.path.join(os.getcwd(), "app", CONFIG_FILE)
        self._personas = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load config from file or return defaults."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    logger.info(f"Loading judge config from {self.config_path}")
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load judge config: {e}. Using defaults.")
                return DEFAULT_JUDGE_PERSONAS.copy()
        else:
            logger.info("No judge config found. Using defaults.")
            return DEFAULT_JUDGE_PERSONAS.copy()

    def save_config(self, personas: Dict[str, Any]):
        """Save config to file."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(personas, f, indent=4, ensure_ascii=False)
            self._personas = personas
            logger.info("Judge config saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save judge config: {e}")
            raise

    def reset_config(self):
        """Reset to defaults."""
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        self._personas = DEFAULT_JUDGE_PERSONAS.copy()
        logger.info("Judge config reset to defaults.")

    def get_personas(self) -> Dict[str, Any]:
        """Get current personas."""
        return self._personas

# Global instance
config_manager = JudgeConfigManager()
