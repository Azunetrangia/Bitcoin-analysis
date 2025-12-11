# Bitcoin Data Auto-Update System

## Overview
Hệ thống tự động cập nhật dữ liệu Bitcoin hàng ngày từ Binance API vào database.

## Components

### 1. Scripts
- **update_2025_data.py**: Script Python để tải và cập nhật dữ liệu
- **auto_update.sh**: Shell script wrapper với logging
- **install_cron.sh**: Script cài đặt cron job tự động

### 2. Cron Job Schedule
- **Frequency**: Daily (hàng ngày)
- **Time**: 2:00 AM (lúc 2 giờ sáng)
- **Timezone**: System local time

## Installation

### Option 1: Using systemd timer (Recommended for modern Linux)

1. Copy service files:
```bash
sudo cp scripts/bitcoin-update.service /etc/systemd/system/
sudo cp scripts/bitcoin-update.timer /etc/systemd/system/
```

2. Edit service file with correct paths:
```bash
sudo nano /etc/systemd/system/bitcoin-update.service
# Update WorkingDirectory and ExecStart paths
```

3. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable bitcoin-update.timer
sudo systemctl start bitcoin-update.timer
```

4. Check status:
```bash
sudo systemctl status bitcoin-update.timer
sudo systemctl list-timers
```

### Option 2: Using cron (Traditional)

1. Make script executable:
```bash
chmod +x scripts/auto_update.sh
```

2. Install cron job:
```bash
bash scripts/install_cron.sh
```

Or manually:
```bash
crontab -e
# Add this line:
0 2 * * * /home/azune/Documents/coding/Data-analysis-bitcoin/scripts/auto_update.sh
```

3. Verify cron job:
```bash
crontab -l
```

## Manual Testing

Test the update script:
```bash
# Test auto_update.sh
bash scripts/auto_update.sh

# Or test Python script directly
python3 scripts/update_2025_data.py
```

## Logs

### Cron Logs
- Location: `logs/auto_update_YYYYMMDD.log`
- Retention: 30 days
- View today's log:
```bash
tail -f logs/auto_update_$(date +%Y%m%d).log
```

### Systemd Logs
```bash
# View service logs
sudo journalctl -u bitcoin-update.service -f

# View last 50 lines
sudo journalctl -u bitcoin-update.service -n 50
```

## Configuration

Edit `scripts/auto_update.sh` to change:
- `PROJECT_DIR`: Project directory path
- `PYTHON_CMD`: Python executable path
- Cron schedule in crontab or timer file

## Monitoring

### Check Last Update
```sql
-- In DuckDB
SELECT MAX(timestamp) as latest_data
FROM market_data
WHERE symbol = 'BTCUSDT' AND interval = '1h';
```

### Check Log Files
```bash
# View recent logs
ls -lht logs/auto_update_*.log | head -5

# Check for errors
grep -i error logs/auto_update_*.log
```

### Email Notifications (Optional)

Add to cron job:
```bash
MAILTO=your-email@example.com
0 2 * * * /path/to/auto_update.sh
```

## Troubleshooting

### Cron Not Running
```bash
# Check cron service
sudo systemctl status cron

# Check cron logs
grep CRON /var/log/syslog
```

### Permission Issues
```bash
# Ensure script is executable
chmod +x scripts/auto_update.sh

# Check log directory
mkdir -p logs
chmod 755 logs
```

### Python Dependencies
```bash
# Install in cron environment
pip3 install -r requirements.txt --user
```

## Data Flow

```
Binance API → update_2025_data.py → DuckDB
                     ↓
              auto_update.sh (wrapper)
                     ↓
         Cron/Systemd Timer (scheduler)
                     ↓
              logs/auto_update_*.log
```

## Schedule Details

| Time | Action | Duration |
|------|--------|----------|
| 02:00 | Start update | - |
| 02:00-02:05 | Download from Binance | ~5 min |
| 02:05-02:06 | Update database | ~1 min |
| 02:06 | Complete | - |

## Backup Recommendations

1. **Database Backup** (before update):
```bash
cp data/bitcoin_market.db data/bitcoin_market.db.backup
```

2. **Automated Backup** (add to cron):
```bash
# Backup database before update
0 1 * * * cp /path/to/bitcoin_market.db /path/to/backups/bitcoin_market_$(date +\%Y\%m\%d).db
```

3. **Retention Policy**:
- Keep daily backups for 7 days
- Keep weekly backups for 4 weeks
- Keep monthly backups for 6 months

## Security Notes

1. **File Permissions**:
```bash
chmod 700 scripts/auto_update.sh
chmod 600 logs/*.log
```

2. **API Keys**: Ensure Binance API keys (if used) are in secure config files with restricted permissions

3. **Log Rotation**: Automatic cleanup of logs older than 30 days

## Future Enhancements

- [ ] Add email/Telegram notifications on failure
- [ ] Implement retry mechanism for failed downloads
- [ ] Add data validation checks
- [ ] Create dashboard for monitoring update status
- [ ] Support multiple symbols/intervals
- [ ] Implement incremental updates (only fetch new data)
