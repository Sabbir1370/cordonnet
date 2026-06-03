"""Load and manage YAML configuration."""
from pathlib import Path
from typing import Optional
import yaml
from cordonnet.models.config import AppConfig
from pydantic import ValidationError
import logging

logger = logging.getLogger("cordonnet.app")

DEFAULT_CONFIG_PATH = Path("config/default.yaml")
SYSTEM_CONFIG_PATH = Path("/etc/cordonnet/config.yaml")

class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None):
        self.path = config_path or SYSTEM_CONFIG_PATH
        if not self.path.exists():
            # Fall back to default in project
            self.path = DEFAULT_CONFIG_PATH
        self.config: Optional[AppConfig] = None
        self.load()

    def load(self) -> AppConfig:
        """Load and validate configuration from YAML."""
        if not self.path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.path}")
        with open(self.path) as f:
            data = yaml.safe_load(f)
        try:
            self.config = AppConfig(**data)
        except ValidationError as e:
            logger.error("Invalid configuration: %s", e)
            raise
        return self.config

    def save(self) -> None:
        """Write current config back to the same file."""
        if self.config is None:
            raise RuntimeError("No configuration loaded.")
        with open(self.path, 'w') as f:
            yaml.dump(self.config.model_dump(), f, default_flow_style=False)

    def get(self) -> AppConfig:
        if self.config is None:
            raise RuntimeError("Configuration not loaded.")
        return self.config