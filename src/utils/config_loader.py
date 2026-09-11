import os
import yaml
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv
from src.utils.logger import logger

load_dotenv()

DEFAULT_CONFIG_PATH = Path("config/config.yaml")

class ConfigLoader:
    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.config: Dict[str, Any] = self._load_config()
        self._apply_env_overrides()

    def _load_config(self) -> Dict[str, Any]:
        """YAML yapılandırma dosyasını yükler."""
        if not self.config_path.exists():
            logger.warning(f"Yapılandırma dosyası bulunamadı: {self.config_path}, varsayılan örnek aranıyor...")
            example_path = Path("config/config.example.yaml")
            if example_path.exists():
                with open(example_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            return {}

        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _apply_env_overrides(self):
        """Ortam değişkenlerinden gelen gizli veya dinamik değerleri config üzerine yazar."""
        # AI
        if "ai" not in self.config:
            self.config["ai"] = {}
        if os.getenv("GEMINI_API_KEY"):
            self.config["ai"]["api_key"] = os.getenv("GEMINI_API_KEY")

        # Email
        if "email" not in self.config:
            self.config["email"] = {}
        if os.getenv("SMTP_HOST"):
            self.config["email"]["smtp_host"] = os.getenv("SMTP_HOST")
        if os.getenv("SMTP_PORT"):
            self.config["email"]["smtp_port"] = int(os.getenv("SMTP_PORT"))
        if os.getenv("SMTP_USER"):
            self.config["email"]["smtp_user"] = os.getenv("SMTP_USER")
        if os.getenv("SMTP_PASSWORD"):
            self.config["email"]["smtp_password"] = os.getenv("SMTP_PASSWORD")
        if os.getenv("SENDER_EMAIL"):
            self.config["email"]["sender_email"] = os.getenv("SENDER_EMAIL")
        if os.getenv("RECIPIENT_EMAIL"):
            self.config["email"]["recipient_email"] = os.getenv("RECIPIENT_EMAIL")

        # Google Sheets
        if "google_sheets" not in self.config:
            self.config["google_sheets"] = {}
        if os.getenv("GOOGLE_SHEETS_ENABLED"):
            self.config["google_sheets"]["enabled"] = os.getenv("GOOGLE_SHEETS_ENABLED").lower() in ("true", "1", "yes")
        if os.getenv("GOOGLE_SHEETS_SPREADSHEET_NAME"):
            self.config["google_sheets"]["spreadsheet_name"] = os.getenv("GOOGLE_SHEETS_SPREADSHEET_NAME")
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            self.config["google_sheets"]["credentials_json"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    def get(self, key_path: str, default: Any = None) -> Any:
        """Nokta notasyonu ile config değerine erişim sağlar (ör: 'search_criteria.job_titles')."""
        keys = key_path.split(".")
        current = self.config
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

# Tekil örnek
config = ConfigLoader()
