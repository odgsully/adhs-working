"""Configuration management using Pydantic Settings."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="ADHS_",
    )

    # Paths
    raw_dir: Path = Field(
        default=Path("./raw"),
        description="Directory containing raw ADHS Excel files",
    )
    output_dir: Path = Field(
        default=Path("./output"),
        description="Directory for output files",
    )
    field_map_path: Path = Field(
        default=Path("./field_map.yml"),
        description="Path to field mapping YAML file",
    )
    field_map_todo_path: Path = Field(
        default=Path("./field_map.TODO.yml"),
        description="Path to TODO field mapping YAML file",
    )

    # Processing options
    dry_run: bool = Field(
        default=False,
        description="Run without writing output files",
    )
    month: str = Field(
        ...,
        description="Processing month in YYYY-MM format",
        pattern=r"^\d{4}-\d{2}$",
    )

    # Fuzzy matching
    fuzzy_threshold: float = Field(
        default=80.0,
        description="Fuzzy matching threshold (0-100)",
        ge=0,
        le=100,
    )

    # MCAO API (stub for future)
    mcao_api_key: Optional[str] = Field(
        default=None,
        description="MCAO API key for geocoding",
    )
    mcao_api_url: str = Field(
        default="https://api.mcao.example.com",
        description="MCAO API base URL",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )


def get_settings(**kwargs) -> Settings:
    """Get settings instance with optional overrides."""
    return Settings(**kwargs)