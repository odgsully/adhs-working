"""CLI interface for ADHS ETL pipeline."""

# Import from enhanced CLI
from .cli_enhanced import app, main  # noqa: F401 - app re-exported for entry point

if __name__ == "__main__":
    main()
