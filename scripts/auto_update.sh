#!/bin/bash

# Auto Update Bitcoin Data - Daily Cron Job
# Purpose: Download latest Bitcoin data and update database
# Schedule: Run daily at 2:00 AM

# Configuration
PROJECT_DIR="/home/azune/Documents/coding/Data-analysis-bitcoin"
PYTHON_CMD="/usr/bin/python3"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/auto_update_$(date +%Y%m%d).log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Redirect all output to log file
exec >> "$LOG_FILE" 2>&1

echo "=========================================="
echo "Bitcoin Data Auto-Update"
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# Change to project directory
cd "$PROJECT_DIR" || exit 1

# Detect Python command with conda
if command -v conda &> /dev/null; then
    echo "Using conda environment..."
    eval "$(conda shell.bash hook)"
    # Conda base environment should have all packages
    PYTHON_CMD="python"
elif [ -d "venv" ]; then
    echo "Activating virtual environment (venv)..."
    source venv/bin/activate
    PYTHON_CMD="python"
elif [ -d ".venv" ]; then
    echo "Activating virtual environment (.venv)..."
    source .venv/bin/activate
    PYTHON_CMD="python"
fi

# Run update script
echo ""
echo "Running incremental update script..."
"$PYTHON_CMD" "$PROJECT_DIR/scripts/incremental_update.py"

UPDATE_STATUS=$?

echo ""
echo "=========================================="
if [ $UPDATE_STATUS -eq 0 ]; then
    echo "✅ Update completed successfully"
else
    echo "❌ Update failed with exit code: $UPDATE_STATUS"
fi
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# Keep only last 30 days of logs
find "$LOG_DIR" -name "auto_update_*.log" -type f -mtime +30 -delete

exit $UPDATE_STATUS
