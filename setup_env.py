#!/usr/bin/env python3
"""
Setup script to create .env file with MCAO API key
"""

import os
from pathlib import Path

def create_env_file():
    """Create .env file with MCAO API configuration."""

    env_content = """# ADHS ETL Environment Configuration

# MCAO API Configuration
MCAO_API_KEY=cc6f7947-2054-479b-ae49-f3fa1c57f3d8

# Fuzzy Matching Threshold (0-100)
# Higher values = stricter matching
FUZZY_THRESHOLD=80.0

# Logging Configuration
LOG_LEVEL=INFO

# Optional: Database connection
# DATABASE_URL=postgresql://user:password@localhost:5432/adhs_etl

# Optional: Output directories (defaults to current directory)
# OUTPUT_DIR=./output
# TEMP_DIR=./temp

# Optional: Processing configuration
# BATCH_SIZE=1000
# MAX_WORKERS=4
"""

    env_path = Path(".env")

    if env_path.exists():
        response = input(".env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Aborted. Existing .env file preserved.")
            return

    try:
        env_path.write_text(env_content)
        print(f"✅ Created .env file with MCAO API key")
        print(f"   MCAO_API_KEY=cc6f7947-2054-479b-ae49-f3fa1c57f3d8")
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")

if __name__ == "__main__":
    create_env_file()