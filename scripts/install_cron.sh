#!/bin/bash

# Install Cron Job for Bitcoin Data Auto-Update
# This script sets up automatic daily updates at 2:00 AM

# Configuration
PROJECT_DIR="/home/azune/Documents/coding/Data-analysis-bitcoin"
SCRIPT_PATH="$PROJECT_DIR/scripts/auto_update.sh"

echo "=========================================="
echo "Bitcoin Data Auto-Update Installation"
echo "=========================================="
echo ""

# Check if script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Error: auto_update.sh not found at $SCRIPT_PATH"
    exit 1
fi

# Make script executable
echo "Making script executable..."
chmod +x "$SCRIPT_PATH"

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Check current crontab
echo ""
echo "Current crontab entries:"
crontab -l 2>/dev/null | grep -v "^#" | grep -v "^$" || echo "(no cron jobs)"

echo ""
echo "=========================================="
echo "Installing cron job..."
echo "=========================================="

# Backup current crontab
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null

# Add new cron job (if not already exists)
(crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH"; echo "# Bitcoin Data Auto-Update - Daily at 2:00 AM"; echo "0 2 * * * $SCRIPT_PATH") | crontab -

if [ $? -eq 0 ]; then
    echo "✅ Cron job installed successfully!"
    echo ""
    echo "Schedule: Daily at 2:00 AM"
    echo "Script: $SCRIPT_PATH"
    echo "Logs: $PROJECT_DIR/logs/auto_update_YYYYMMDD.log"
else
    echo "❌ Failed to install cron job"
    exit 1
fi

echo ""
echo "=========================================="
echo "Verification"
echo "=========================================="
echo ""
echo "Current crontab:"
crontab -l

echo ""
echo "=========================================="
echo "Testing"
echo "=========================================="
echo ""
echo "To test the update script manually, run:"
echo "bash $SCRIPT_PATH"
echo ""
echo "To view logs:"
echo "tail -f $PROJECT_DIR/logs/auto_update_\$(date +%Y%m%d).log"
echo ""
echo "To remove the cron job:"
echo "crontab -e"
echo "(then delete the line with auto_update.sh)"
echo ""
echo "=========================================="
echo "✅ Installation Complete!"
echo "=========================================="
