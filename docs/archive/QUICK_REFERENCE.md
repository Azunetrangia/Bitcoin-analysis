# Quick Reference - Auto Update System

## Status Check

### Check if cron is installed and running:
```bash
crontab -l
```

### Check latest database update:
```bash
cd /home/azune/Documents/coding/Data-analysis-bitcoin
python -c "
import duckdb
conn = duckdb.connect('data/bitcoin_market.db')
result = conn.execute(\"SELECT MAX(timestamp) as latest, COUNT(*) as total FROM market_data WHERE symbol='BTCUSDT' AND interval='1h'\").fetchone()
print(f'Latest: {result[0]}')
print(f'Total rows: {result[1]:,}')
"
```

### View recent logs:
```bash
tail -50 /home/azune/Documents/coding/Data-analysis-bitcoin/logs/auto_update_$(date +%Y%m%d).log
```

### Check for errors in logs:
```bash
grep -i error /home/azune/Documents/coding/Data-analysis-bitcoin/logs/auto_update_*.log
```

## Manual Operations

### Run update manually:
```bash
cd /home/azune/Documents/coding/Data-analysis-bitcoin
bash scripts/auto_update.sh
```

### Run update script directly (for testing):
```bash
cd /home/azune/Documents/coding/Data-analysis-bitcoin
python scripts/incremental_update.py
```

## Cron Management

### Remove cron job:
```bash
crontab -e
# Delete the line with auto_update.sh
```

### Reinstall cron job:
```bash
bash /home/azune/Documents/coding/Data-analysis-bitcoin/scripts/install_cron.sh
```

### Edit cron schedule:
```bash
crontab -e
# Change "0 2 * * *" to your desired schedule
# Examples:
# 0 3 * * * - Run at 3:00 AM
# 0 */6 * * * - Run every 6 hours
# 0 0 * * * - Run at midnight
```

## Monitoring

### Check cron logs (system-wide):
```bash
grep CRON /var/log/syslog | tail -20
```

### View all auto-update logs:
```bash
ls -lh /home/azune/Documents/coding/Data-analysis-bitcoin/logs/
```

### Monitor today's update in real-time:
```bash
tail -f /home/azune/Documents/coding/Data-analysis-bitcoin/logs/auto_update_$(date +%Y%m%d).log
```

## Database Operations

### Check database size:
```bash
du -h /home/azune/Documents/coding/Data-analysis-bitcoin/data/bitcoin_market.db
```

### Backup database:
```bash
cp /home/azune/Documents/coding/Data-analysis-bitcoin/data/bitcoin_market.db \
   /home/azune/Documents/coding/Data-analysis-bitcoin/data/bitcoin_market.db.backup_$(date +%Y%m%d)
```

### Verify data integrity:
```bash
cd /home/azune/Documents/coding/Data-analysis-bitcoin
python -c "
import duckdb
conn = duckdb.connect('data/bitcoin_market.db')
print('Checking for gaps in data...')
result = conn.execute('''
SELECT COUNT(*) as total, 
       MIN(timestamp) as earliest, 
       MAX(timestamp) as latest
FROM market_data 
WHERE symbol='BTCUSDT' AND interval='1h'
''').fetchone()
print(f'Total: {result[0]:,}')
print(f'Range: {result[1]} to {result[2]}')
"
```

## Troubleshooting

### If update fails:

1. Check log file for errors
2. Verify internet connection
3. Test script manually: `python scripts/incremental_update.py`
4. Check if database is accessible
5. Ensure enough disk space: `df -h`

### If no data is being added:

This is normal if the database is already up-to-date. Check the log message:
- "✅ No new unique data to add" - Database is current
- "✅ Database is up-to-date" - No updates needed

### If seeing duplicate key errors:

The script handles this automatically by filtering existing timestamps.
If you still see errors, the deduplication logic is working correctly.

## Schedule Information

- **Current Schedule**: Daily at 2:00 AM
- **Next Run**: Check with `systemctl list-timers` or cron logs
- **Duration**: ~1-5 seconds (incremental updates are fast)
- **Data Size**: Usually 1-24 new rows per day (hourly data)

## Files

- **Update Script**: `scripts/incremental_update.py`
- **Shell Wrapper**: `scripts/auto_update.sh`
- **Cron Installer**: `scripts/install_cron.sh`
- **Logs Directory**: `logs/`
- **Database**: `data/bitcoin_market.db`
- **Documentation**: `docs/AUTO_UPDATE.md`
