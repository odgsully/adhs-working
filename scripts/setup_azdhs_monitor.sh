#!/bin/bash
#
# AZDHS Monitor Setup Script
#
# This script sets up the AZDHS monitoring system including:
# - Installing Playwright and browser dependencies
# - Configuring the macOS LaunchAgent for daily scheduling
# - Verifying environment variables
#
# Usage:
#   chmod +x scripts/setup_azdhs_monitor.sh
#   ./scripts/setup_azdhs_monitor.sh

set -e

echo "========================================"
echo "AZDHS Monitor Setup"
echo "========================================"
echo

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"
echo "[INFO] Working directory: $PROJECT_DIR"
echo

# Step 1: Install Python dependencies
echo "[1/5] Installing Python dependencies..."
poetry add playwright python-dotenv --quiet 2>/dev/null || true
poetry install --quiet
echo "      Done."
echo

# Step 2: Install Playwright browsers
echo "[2/5] Installing Playwright browsers (Chromium)..."
poetry run playwright install chromium
echo "      Done."
echo

# Step 3: Check environment variables
echo "[3/5] Checking environment variables..."
if [ -f .env ]; then
    source .env 2>/dev/null || true

    MISSING_VARS=()

    if [ -z "$AZDHS_SLACK_WEBHOOK_URL" ]; then
        MISSING_VARS+=("AZDHS_SLACK_WEBHOOK_URL")
    fi

    if [ -z "$AZDHS_GMAIL_USER" ] || [ -z "$AZDHS_GMAIL_APP_PASSWORD" ]; then
        MISSING_VARS+=("AZDHS_GMAIL_USER / AZDHS_GMAIL_APP_PASSWORD")
    fi

    if [ -z "$AZDHS_NOTIFY_EMAIL" ]; then
        MISSING_VARS+=("AZDHS_NOTIFY_EMAIL")
    fi

    if [ ${#MISSING_VARS[@]} -gt 0 ]; then
        echo "      [WARN] Missing environment variables:"
        for var in "${MISSING_VARS[@]}"; do
            echo "             - $var"
        done
        echo "      Please add these to your .env file."
    else
        echo "      All notification variables configured."
    fi
else
    echo "      [WARN] No .env file found. Copy .env.sample to .env and configure:"
    echo "             cp .env.sample .env"
fi
echo

# Step 4: Test the monitor (dry run)
echo "[4/5] Testing monitor (dry run)..."
poetry run python scripts/azdhs_monitor.py --check-only --dry-run 2>&1 | head -20
echo "      Test complete."
echo

# Step 5: Setup macOS LaunchAgent (optional)
echo "[5/5] macOS LaunchAgent Setup"
echo

PLIST_FILE="$SCRIPT_DIR/com.azdhs.monitor.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
DEST_PLIST="$LAUNCH_AGENTS_DIR/com.azdhs.monitor.plist"

if [ "$(uname)" == "Darwin" ]; then
    echo "      Would you like to install the daily scheduler? (y/n)"
    read -r INSTALL_LAUNCHD

    if [ "$INSTALL_LAUNCHD" == "y" ] || [ "$INSTALL_LAUNCHD" == "Y" ]; then
        # Create LaunchAgents directory if needed
        mkdir -p "$LAUNCH_AGENTS_DIR"

        # Update paths in plist
        POETRY_PATH=$(which poetry 2>/dev/null || echo "/Users/$(whoami)/.local/bin/poetry")

        sed -e "s|/Users/garrettsullivan/.local/bin/poetry|$POETRY_PATH|g" \
            -e "s|/Users/garrettsullivan/Desktop/BHRF/Data_Recourses/LANDSCRAPE/adhs-working|$PROJECT_DIR|g" \
            "$PLIST_FILE" > "$DEST_PLIST"

        # Unload if already loaded
        launchctl unload "$DEST_PLIST" 2>/dev/null || true

        # Load the agent
        launchctl load "$DEST_PLIST"

        echo "      LaunchAgent installed and loaded."
        echo "      The monitor will run daily at 6:00 AM."
        echo
        echo "      Useful commands:"
        echo "        Run now:   launchctl start com.azdhs.monitor"
        echo "        Check:     launchctl list | grep azdhs"
        echo "        Unload:    launchctl unload ~/Library/LaunchAgents/com.azdhs.monitor.plist"
        echo "        Logs:      tail -f /tmp/azdhs-monitor.stdout.log"
    else
        echo "      Skipping LaunchAgent installation."
        echo "      You can install manually later with:"
        echo "        cp scripts/com.azdhs.monitor.plist ~/Library/LaunchAgents/"
        echo "        launchctl load ~/Library/LaunchAgents/com.azdhs.monitor.plist"
    fi
else
    echo "      [INFO] Not macOS. For Linux, add this to crontab:"
    echo "        0 6 * * * cd $PROJECT_DIR && poetry run python scripts/azdhs_monitor.py --notify"
fi
echo

echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo
echo "Quick Commands:"
echo "  Check for new data:     poetry run python scripts/azdhs_monitor.py --check-only"
echo "  Download new month:     poetry run python scripts/azdhs_monitor.py --notify"
echo "  Download specific:      poetry run python scripts/azdhs_monitor.py --month 1.26 --force"
echo "  Test notifications:     poetry run python scripts/azdhs_notify.py --all"
echo "  Sync to Supabase:       poetry run python scripts/azdhs_supabase.py --month 1.25"
echo
echo "Logs:"
echo "  macOS: /tmp/azdhs-monitor.stdout.log"
echo "  GitHub Actions: See workflow runs in repository"
echo
