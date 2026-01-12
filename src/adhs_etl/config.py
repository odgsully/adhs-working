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


class EcorpSettings(BaseSettings):
    """Ecorp scraping configuration with environment variable support.

    All settings can be overridden via environment variables with the
    ADHS_ECORP_ prefix, e.g., ADHS_ECORP_BASE_URL.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="ADHS_ECORP_",
    )

    # URLs
    # NOTE: As of January 2026, Arizona Business Connect requires authentication
    # for entity searches. The old public eCorp search is no longer available.
    base_url: str = Field(
        default="https://arizonabusinesscenter.azcc.gov/businesssearch",
        description="Arizona Business Connect business search (requires login for results)",
    )
    login_url: str = Field(
        default="https://arizonabusinesscenter.azcc.gov/login",
        description="Arizona Business Connect login page",
    )
    authenticated_url: str = Field(
        default="https://arizonabusinesscenter.azcc.gov/entitysearch/index",
        description="Arizona Business Connect authenticated entity search",
    )
    legacy_url: str = Field(
        default="https://ecorp.azcc.gov/EntitySearch/Index",
        description="Legacy eCorp URL (offline - site decommissioned Jan 2, 2026)",
    )

    # Authentication credentials (optional - for automated login)
    email: Optional[str] = Field(
        default=None,
        description="Arizona Business Connect account email for authenticated searches",
    )
    password: Optional[str] = Field(
        default=None,
        description="Arizona Business Connect account password (use env var ADHS_ECORP_PASSWORD)",
    )

    # Timing (anti-detection)
    min_delay: float = Field(
        default=2.0,
        description="Minimum delay between requests (seconds)",
        ge=0.5,
        le=30.0,
    )
    max_delay: float = Field(
        default=5.0,
        description="Maximum delay between requests (seconds)",
        ge=1.0,
        le=60.0,
    )
    page_load_timeout: int = Field(
        default=10,
        description="WebDriverWait timeout for page loads (seconds)",
        ge=5,
        le=120,
    )
    selector_retry_timeout: int = Field(
        default=5,
        description="Timeout per selector in fallback chain (seconds)",
        ge=1,
        le=30,
    )

    # Feature flags
    enable_captcha_detection: bool = Field(
        default=True,
        description="Enable CAPTCHA detection (future-proofing)",
    )
    enable_rate_limit_detection: bool = Field(
        default=True,
        description="Enable rate limit/blocking detection",
    )
    enable_monitoring: bool = Field(
        default=True,
        description="Enable monitoring and alerting",
    )
    use_legacy_scraper: bool = Field(
        default=False,
        description="Use legacy scraper instead of new implementation",
    )
    checkpoint_interval: int = Field(
        default=50,
        description="Save checkpoint every N records",
        ge=10,
        le=500,
    )
    health_check_interval: int = Field(
        default=25,
        description="Perform health check every N records",
        ge=5,
        le=100,
    )

    # Monitoring
    slack_webhook_url: Optional[str] = Field(
        default=None,
        description="Slack webhook URL for failure alerts",
    )
    alert_on_captcha: bool = Field(
        default=True,
        description="Send alert when CAPTCHA detected",
    )
    alert_on_rate_limit: bool = Field(
        default=True,
        description="Send alert when rate limited",
    )

    # Browser settings
    headless: bool = Field(
        default=True,
        description="Run browser in headless mode",
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="Custom user agent string (None = browser default)",
    )


def get_ecorp_settings(**kwargs) -> EcorpSettings:
    """Get Ecorp settings instance with optional overrides."""
    return EcorpSettings(**kwargs)